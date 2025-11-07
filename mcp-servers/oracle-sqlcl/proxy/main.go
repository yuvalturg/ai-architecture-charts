package main

import (
	"bufio"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"regexp"
	"strings"
)

type MCPProxy struct {
	cmd      *exec.Cmd
	stdin    io.WriteCloser
	stdout   *bufio.Reader
	requests chan *request
}

type request struct {
	msg          json.RawMessage
	isRequest    bool
	response     chan json.RawMessage
}

type MCPMessage struct {
	ID interface{} `json:"id,omitempty"`
}

type MCPResult struct {
	Content []MCPContent `json:"content,omitempty"`
	IsError bool         `json:"isError,omitempty"`
}

type MCPContent struct {
	Type string `json:"type"`
	Text string `json:"text"`
}

type MCPResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      interface{}     `json:"id,omitempty"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   json.RawMessage `json:"error,omitempty"`
}

var oraErrorPattern = regexp.MustCompile(`(?i)(ORA-\d+|Error:.*ORA-\d+)`)

func NewMCPProxy() (*MCPProxy, error) {
	sqlPath := os.Getenv("SQL_PATH")
	if sqlPath == "" {
		sqlPath = "/opt/oracle/sqlcl/bin/sql"
	}

	log.Printf("Starting SQLcl MCP at: %s", sqlPath)

	cmd := exec.Command(sqlPath, "-mcp")
	stdin, _ := cmd.StdinPipe()
	stdout, _ := cmd.StdoutPipe()
	stderr, _ := cmd.StderrPipe()

	go func() {
		scanner := bufio.NewScanner(stderr)
		for scanner.Scan() {
			log.Printf("[SQLcl stderr] %s", scanner.Text())
		}
	}()

	if err := cmd.Start(); err != nil {
		return nil, err
	}

	log.Printf("Started SQLcl MCP (PID: %d)", cmd.Process.Pid)

	proxy := &MCPProxy{
		cmd:      cmd,
		stdin:    stdin,
		stdout:   bufio.NewReader(stdout),
		requests: make(chan *request, 100),
	}

	go proxy.processRequests()

	return proxy, nil
}

func (p *MCPProxy) processRequests() {
	for req := range p.requests {
		log.Printf("Sending to SQLcl: %s", string(req.msg))

		// Write to stdio (newline-delimited JSON)
		p.stdin.Write(append(req.msg, '\n'))

		// Only read response if this is a request (has ID), not a notification
		if req.isRequest {
			// Read from stdio (newline-delimited JSON)
			line, err := p.stdout.ReadBytes('\n')
			if err != nil {
				log.Printf("Error reading from SQLcl: %v", err)
				close(req.response)
				continue
			}

			log.Printf("Received from SQLcl: %s", string(line[:len(line)-1]))

			// Check for Oracle errors and mark as error if found
			response := line[:len(line)-1]
			response = markOracleErrors(response)

			req.response <- response
		}
		close(req.response)
	}
}

func markOracleErrors(response json.RawMessage) json.RawMessage {
	var mcpResp MCPResponse
	if err := json.Unmarshal(response, &mcpResp); err != nil {
		return response
	}

	// Only process if there's a result
	if len(mcpResp.Result) == 0 {
		return response
	}

	var result MCPResult
	if err := json.Unmarshal(mcpResp.Result, &result); err != nil {
		return response
	}

	// Check if already marked as error
	if result.IsError {
		return response
	}

	// Check content for Oracle errors
	hasOracleError := false
	for _, content := range result.Content {
		if content.Type == "text" && (oraErrorPattern.MatchString(content.Text) ||
			strings.Contains(content.Text, "Error:")) {
			hasOracleError = true
			log.Printf("Detected Oracle error in response: %s", content.Text)
			break
		}
	}

	if hasOracleError {
		result.IsError = true
		newResult, _ := json.Marshal(result)
		mcpResp.Result = newResult
		newResponse, _ := json.Marshal(mcpResp)
		return newResponse
	}

	return response
}

func (p *MCPProxy) Handle(w http.ResponseWriter, r *http.Request) {
	log.Printf("HTTP request from %s %s", r.RemoteAddr, r.URL.Path)

	// Read HTTP JSON body
	var msg json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&msg); err != nil {
		log.Printf("Failed to decode HTTP body: %v", err)
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	log.Printf("Received HTTP request: %s", string(msg))

	// Check if this is a request (has ID) or notification (no ID)
	var mcpMsg MCPMessage
	json.Unmarshal(msg, &mcpMsg)
	isRequest := mcpMsg.ID != nil

	// Send request to sql -mcp
	req := &request{
		msg:       msg,
		isRequest: isRequest,
		response:  make(chan json.RawMessage, 1),
	}
	p.requests <- req

	// Wait for response (only if it's a request)
	if isRequest {
		response, ok := <-req.response
		if !ok {
			log.Printf("Failed to get response from SQLcl")
			http.Error(w, "Failed to get response", http.StatusInternalServerError)
			return
		}

		log.Printf("Sending HTTP response: %s", string(response))

		// Write HTTP JSON response
		w.Header().Set("Content-Type", "application/json")
		w.Write(response)
	} else {
		// For notifications, return 202 Accepted
		<-req.response // Wait for processing to complete
		log.Printf("Notification processed")
		w.WriteHeader(http.StatusAccepted)
	}
}

func main() {
	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}

	log.Printf("MCP Streamable HTTP Proxy starting...")

	proxy, err := NewMCPProxy()
	if err != nil {
		log.Fatalf("Failed to create proxy: %v", err)
	}

	http.HandleFunc("/", proxy.Handle)
	log.Printf("Listening on port %s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}

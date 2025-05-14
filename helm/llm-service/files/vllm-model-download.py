import sys

from vllm.engine.arg_utils import AsyncEngineArgs
from vllm.entrypoints.openai.cli_args import make_arg_parser
from vllm.model_executor.model_loader.loader import get_model_loader
from vllm.utils import FlexibleArgumentParser

def vllm_download(args):
    parser = FlexibleArgumentParser()
    parser = make_arg_parser(parser)
    args = parser.parse_args(args)
    engine_args = AsyncEngineArgs.from_cli_args(args)
    model_config = engine_args.create_model_config()
    load_config = engine_args.create_load_config()
    model_loader = get_model_loader(load_config)
    model_loader.download_model(model_config)

if __name__ == "__main__":
    vllm_download(sys.argv[1:])

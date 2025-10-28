-- Oracle-compatible TPC-DS Schema
-- Based on official TPC-DS specification but adapted for Oracle data types

-- Drop existing tables first
BEGIN
   FOR c IN (SELECT table_name FROM user_tables WHERE table_name IN (
       'DBGEN_VERSION', 'CUSTOMER_ADDRESS', 'CUSTOMER_DEMOGRAPHICS', 'DATE_DIM',
       'WAREHOUSE', 'SHIP_MODE', 'TIME_DIM', 'REASON', 'INCOME_BAND', 'ITEM',
       'STORE', 'CALL_CENTER', 'CUSTOMER', 'WEB_SITE', 'STORE_RETURNS',
       'HOUSEHOLD_DEMOGRAPHICS', 'WEB_PAGE', 'PROMOTION', 'CATALOG_PAGE',
       'INVENTORY', 'CATALOG_RETURNS', 'WEB_RETURNS', 'WEB_SALES',
       'CATALOG_SALES', 'STORE_SALES'
   )) LOOP
      EXECUTE IMMEDIATE ('DROP TABLE ' || c.table_name || ' CASCADE CONSTRAINTS');
   END LOOP;
END;
/

create table dbgen_version
(
    dv_version                varchar2(16),
    dv_create_date            date,
    dv_create_time            timestamp,
    dv_cmdline_args           varchar2(200)
);

create table customer_address
(
    ca_address_sk             number                not null,
    ca_address_id             char(16)              not null,
    ca_street_number          char(10),
    ca_street_name            varchar2(60),
    ca_street_type            char(15),
    ca_suite_number           char(10),
    ca_city                   varchar2(60),
    ca_county                 varchar2(30),
    ca_state                  char(2),
    ca_zip                    char(10),
    ca_country                varchar2(20),
    ca_gmt_offset             number(5,2),
    ca_location_type          char(20),
    primary key (ca_address_sk)
);

create table customer_demographics
(
    cd_demo_sk                number                not null,
    cd_gender                 char(1),
    cd_marital_status         char(1),
    cd_education_status       char(20),
    cd_purchase_estimate      number,
    cd_credit_rating          char(10),
    cd_dep_count              number,
    cd_dep_employed_count     number,
    cd_dep_college_count      number,
    primary key (cd_demo_sk)
);

create table date_dim
(
    d_date_sk                 number                not null,
    d_date_id                 char(16)              not null,
    d_date                    date,
    d_month_seq               number,
    d_week_seq                number,
    d_quarter_seq             number,
    d_year                    number,
    d_dow                     number,
    d_moy                     number,
    d_dom                     number,
    d_qoy                     number,
    d_fy_year                 number,
    d_fy_quarter_seq          number,
    d_fy_week_seq             number,
    d_day_name                char(9),
    d_quarter_name            char(6),
    d_holiday                 char(1),
    d_weekend                 char(1),
    d_following_holiday       char(1),
    d_first_dom               number,
    d_last_dom                number,
    d_same_day_ly             number,
    d_same_day_lq             number,
    d_current_day             char(1),
    d_current_week            char(1),
    d_current_month           char(1),
    d_current_quarter         char(1),
    d_current_year            char(1),
    primary key (d_date_sk)
);

create table warehouse
(
    w_warehouse_sk            number                not null,
    w_warehouse_id            char(16)              not null,
    w_warehouse_name          varchar2(20),
    w_warehouse_sq_ft         number,
    w_street_number           char(10),
    w_street_name             varchar2(60),
    w_street_type             char(15),
    w_suite_number            char(10),
    w_city                    varchar2(60),
    w_county                  varchar2(30),
    w_state                   char(2),
    w_zip                     char(10),
    w_country                 varchar2(20),
    w_gmt_offset              number(5,2),
    primary key (w_warehouse_sk)
);

create table ship_mode
(
    sm_ship_mode_sk           number                not null,
    sm_ship_mode_id           char(16)              not null,
    sm_type                   char(30),
    sm_code                   char(10),
    sm_carrier                char(20),
    sm_contract               char(20),
    primary key (sm_ship_mode_sk)
);

create table time_dim
(
    t_time_sk                 number                not null,
    t_time_id                 char(16)              not null,
    t_time                    number,
    t_hour                    number,
    t_minute                  number,
    t_second                  number,
    t_am_pm                   char(2),
    t_shift                   char(20),
    t_sub_shift               char(20),
    t_meal_time               char(20),
    primary key (t_time_sk)
);

create table reason
(
    r_reason_sk               number                not null,
    r_reason_id               char(16)              not null,
    r_reason_desc             char(100),
    primary key (r_reason_sk)
);

create table income_band
(
    ib_income_band_sk         number                not null,
    ib_lower_bound            number,
    ib_upper_bound            number,
    primary key (ib_income_band_sk)
);

create table item
(
    i_item_sk                 number                not null,
    i_item_id                 char(16)              not null,
    i_rec_start_date          date,
    i_rec_end_date            date,
    i_item_desc               varchar2(200),
    i_current_price           number(7,2),
    i_wholesale_cost          number(7,2),
    i_brand_id                number,
    i_brand                   char(50),
    i_class_id                number,
    i_class                   char(50),
    i_category_id             number,
    i_category                char(50),
    i_manufact_id             number,
    i_manufact                char(50),
    i_size                    char(20),
    i_formulation             char(20),
    i_color                   char(20),
    i_units                   char(10),
    i_container               char(10),
    i_manager_id              number,
    i_product_name            char(50),
    primary key (i_item_sk)
);

create table store
(
    s_store_sk                number                not null,
    s_store_id                char(16)              not null,
    s_rec_start_date          date,
    s_rec_end_date            date,
    s_closed_date_sk          number,
    s_store_name              varchar2(50),
    s_number_employees        number,
    s_floor_space             number,
    s_hours                   char(20),
    s_manager                 varchar2(40),
    s_market_id               number,
    s_geography_class         varchar2(100),
    s_market_desc             varchar2(100),
    s_market_manager          varchar2(40),
    s_division_id             number,
    s_division_name           varchar2(50),
    s_company_id              number,
    s_company_name            varchar2(50),
    s_street_number           varchar2(10),
    s_street_name             varchar2(60),
    s_street_type             char(15),
    s_suite_number            char(10),
    s_city                    varchar2(60),
    s_county                  varchar2(30),
    s_state                   char(2),
    s_zip                     char(10),
    s_country                 varchar2(20),
    s_gmt_offset              number(5,2),
    s_tax_precentage          number(5,2),
    primary key (s_store_sk)
);

create table call_center
(
    cc_call_center_sk         number                not null,
    cc_call_center_id         char(16)              not null,
    cc_rec_start_date         date,
    cc_rec_end_date           date,
    cc_closed_date_sk         number,
    cc_open_date_sk           number,
    cc_name                   varchar2(50),
    cc_class                  varchar2(50),
    cc_employees              number,
    cc_sq_ft                  number,
    cc_hours                  char(20),
    cc_manager                varchar2(40),
    cc_mkt_id                 number,
    cc_mkt_class              char(50),
    cc_mkt_desc               varchar2(100),
    cc_market_manager         varchar2(40),
    cc_division               number,
    cc_division_name          varchar2(50),
    cc_company                number,
    cc_company_name           char(50),
    cc_street_number          char(10),
    cc_street_name            varchar2(60),
    cc_street_type            char(15),
    cc_suite_number           char(10),
    cc_city                   varchar2(60),
    cc_county                 varchar2(30),
    cc_state                  char(2),
    cc_zip                    char(10),
    cc_country                varchar2(20),
    cc_gmt_offset             number(5,2),
    cc_tax_percentage         number(5,2),
    primary key (cc_call_center_sk)
);

create table customer
(
    c_customer_sk             number                not null,
    c_customer_id             char(16)              not null,
    c_current_cdemo_sk        number,
    c_current_hdemo_sk        number,
    c_current_addr_sk         number,
    c_first_shipto_date_sk    number,
    c_first_sales_date_sk     number,
    c_salutation              char(10),
    c_first_name              char(20),
    c_last_name               char(30),
    c_preferred_cust_flag     char(1),
    c_birth_day               number,
    c_birth_month             number,
    c_birth_year              number,
    c_birth_country           varchar2(20),
    c_login                   char(13),
    c_email_address           char(50),
    c_last_review_date_sk     number,
    primary key (c_customer_sk)
);

create table web_site
(
    web_site_sk               number                not null,
    web_site_id               char(16)              not null,
    web_rec_start_date        date,
    web_rec_end_date          date,
    web_name                  varchar2(50),
    web_open_date_sk          number,
    web_close_date_sk         number,
    web_class                 varchar2(50),
    web_manager               varchar2(40),
    web_mkt_id                number,
    web_mkt_class             varchar2(50),
    web_mkt_desc              varchar2(100),
    web_market_manager        varchar2(40),
    web_company_id            number,
    web_company_name          char(50),
    web_street_number         char(10),
    web_street_name           varchar2(60),
    web_street_type           char(15),
    web_suite_number          char(10),
    web_city                  varchar2(60),
    web_county                varchar2(30),
    web_state                 char(2),
    web_zip                   char(10),
    web_country               varchar2(20),
    web_gmt_offset            number(5,2),
    web_tax_percentage        number(5,2),
    primary key (web_site_sk)
);

create table store_returns
(
    sr_returned_date_sk       number,
    sr_return_time_sk         number,
    sr_item_sk                number                not null,
    sr_customer_sk            number,
    sr_cdemo_sk               number,
    sr_hdemo_sk               number,
    sr_addr_sk                number,
    sr_store_sk               number,
    sr_reason_sk              number,
    sr_ticket_number          number                not null,
    sr_return_quantity        number,
    sr_return_amt             number(7,2),
    sr_return_tax             number(7,2),
    sr_return_amt_inc_tax     number(7,2),
    sr_fee                    number(7,2),
    sr_return_ship_cost       number(7,2),
    sr_refunded_cash          number(7,2),
    sr_reversed_charge        number(7,2),
    sr_store_credit           number(7,2),
    sr_net_loss               number(7,2),
    primary key (sr_item_sk, sr_ticket_number)
);

create table household_demographics
(
    hd_demo_sk                number                not null,
    hd_income_band_sk         number,
    hd_buy_potential          char(15),
    hd_dep_count              number,
    hd_vehicle_count          number,
    primary key (hd_demo_sk)
);

create table web_page
(
    wp_web_page_sk            number                not null,
    wp_web_page_id            char(16)              not null,
    wp_rec_start_date         date,
    wp_rec_end_date           date,
    wp_creation_date_sk       number,
    wp_access_date_sk         number,
    wp_autogen_flag           char(1),
    wp_customer_sk            number,
    wp_url                    varchar2(100),
    wp_type                   char(50),
    wp_char_count             number,
    wp_link_count             number,
    wp_image_count            number,
    wp_max_ad_count           number,
    primary key (wp_web_page_sk)
);

create table promotion
(
    p_promo_sk                number                not null,
    p_promo_id                char(16)              not null,
    p_start_date_sk           number,
    p_end_date_sk             number,
    p_item_sk                 number,
    p_cost                    number(15,2),
    p_response_target         number,
    p_promo_name              char(50),
    p_channel_dmail           char(1),
    p_channel_email           char(1),
    p_channel_catalog         char(1),
    p_channel_tv              char(1),
    p_channel_radio           char(1),
    p_channel_press           char(1),
    p_channel_event           char(1),
    p_channel_demo            char(1),
    p_channel_details         varchar2(100),
    p_purpose                 char(15),
    p_discount_active         char(1),
    primary key (p_promo_sk)
);

create table catalog_page
(
    cp_catalog_page_sk        number                not null,
    cp_catalog_page_id        char(16)              not null,
    cp_start_date_sk          number,
    cp_end_date_sk            number,
    cp_department             varchar2(50),
    cp_catalog_number         number,
    cp_catalog_page_number    number,
    cp_description            varchar2(100),
    cp_type                   varchar2(100),
    primary key (cp_catalog_page_sk)
);

create table inventory
(
    inv_date_sk               number                not null,
    inv_item_sk               number                not null,
    inv_warehouse_sk          number                not null,
    inv_quantity_on_hand      number,
    primary key (inv_date_sk, inv_item_sk, inv_warehouse_sk)
);

create table catalog_returns
(
    cr_returned_date_sk       number,
    cr_returned_time_sk       number,
    cr_item_sk                number                not null,
    cr_refunded_customer_sk   number,
    cr_refunded_cdemo_sk      number,
    cr_refunded_hdemo_sk      number,
    cr_refunded_addr_sk       number,
    cr_returning_customer_sk  number,
    cr_returning_cdemo_sk     number,
    cr_returning_hdemo_sk     number,
    cr_returning_addr_sk      number,
    cr_call_center_sk         number,
    cr_catalog_page_sk        number,
    cr_ship_mode_sk           number,
    cr_warehouse_sk           number,
    cr_reason_sk              number,
    cr_order_number           number                not null,
    cr_return_quantity        number,
    cr_return_amount          number(7,2),
    cr_return_tax             number(7,2),
    cr_return_amt_inc_tax     number(7,2),
    cr_fee                    number(7,2),
    cr_return_ship_cost       number(7,2),
    cr_refunded_cash          number(7,2),
    cr_reversed_charge        number(7,2),
    cr_store_credit           number(7,2),
    cr_net_loss               number(7,2),
    primary key (cr_item_sk, cr_order_number)
);

create table web_returns
(
    wr_returned_date_sk       number,
    wr_returned_time_sk       number,
    wr_item_sk                number                not null,
    wr_refunded_customer_sk   number,
    wr_refunded_cdemo_sk      number,
    wr_refunded_hdemo_sk      number,
    wr_refunded_addr_sk       number,
    wr_returning_customer_sk  number,
    wr_returning_cdemo_sk     number,
    wr_returning_hdemo_sk     number,
    wr_returning_addr_sk      number,
    wr_web_page_sk            number,
    wr_reason_sk              number,
    wr_order_number           number                not null,
    wr_return_quantity        number,
    wr_return_amt             number(7,2),
    wr_return_tax             number(7,2),
    wr_return_amt_inc_tax     number(7,2),
    wr_fee                    number(7,2),
    wr_return_ship_cost       number(7,2),
    wr_refunded_cash          number(7,2),
    wr_reversed_charge        number(7,2),
    wr_account_credit         number(7,2),
    wr_net_loss               number(7,2),
    primary key (wr_item_sk, wr_order_number)
);

create table web_sales
(
    ws_sold_date_sk           number,
    ws_sold_time_sk           number,
    ws_ship_date_sk           number,
    ws_item_sk                number                not null,
    ws_bill_customer_sk       number,
    ws_bill_cdemo_sk          number,
    ws_bill_hdemo_sk          number,
    ws_bill_addr_sk           number,
    ws_ship_customer_sk       number,
    ws_ship_cdemo_sk          number,
    ws_ship_hdemo_sk          number,
    ws_ship_addr_sk           number,
    ws_web_page_sk            number,
    ws_web_site_sk            number,
    ws_ship_mode_sk           number,
    ws_warehouse_sk           number,
    ws_promo_sk               number,
    ws_order_number           number                not null,
    ws_quantity               number,
    ws_wholesale_cost         number(7,2),
    ws_list_price             number(7,2),
    ws_sales_price            number(7,2),
    ws_ext_discount_amt       number(7,2),
    ws_ext_sales_price        number(7,2),
    ws_ext_wholesale_cost     number(7,2),
    ws_ext_list_price         number(7,2),
    ws_ext_tax                number(7,2),
    ws_coupon_amt             number(7,2),
    ws_ext_ship_cost          number(7,2),
    ws_net_paid               number(7,2),
    ws_net_paid_inc_tax       number(7,2),
    ws_net_paid_inc_ship      number(7,2),
    ws_net_paid_inc_ship_tax  number(7,2),
    ws_net_profit             number(7,2),
    primary key (ws_item_sk, ws_order_number)
);

create table catalog_sales
(
    cs_sold_date_sk           number,
    cs_sold_time_sk           number,
    cs_ship_date_sk           number,
    cs_bill_customer_sk       number,
    cs_bill_cdemo_sk          number,
    cs_bill_hdemo_sk          number,
    cs_bill_addr_sk           number,
    cs_ship_customer_sk       number,
    cs_ship_cdemo_sk          number,
    cs_ship_hdemo_sk          number,
    cs_ship_addr_sk           number,
    cs_call_center_sk         number,
    cs_catalog_page_sk        number,
    cs_ship_mode_sk           number,
    cs_warehouse_sk           number,
    cs_item_sk                number                not null,
    cs_promo_sk               number,
    cs_order_number           number                not null,
    cs_quantity               number,
    cs_wholesale_cost         number(7,2),
    cs_list_price             number(7,2),
    cs_sales_price            number(7,2),
    cs_ext_discount_amt       number(7,2),
    cs_ext_sales_price        number(7,2),
    cs_ext_wholesale_cost     number(7,2),
    cs_ext_list_price         number(7,2),
    cs_ext_tax                number(7,2),
    cs_coupon_amt             number(7,2),
    cs_ext_ship_cost          number(7,2),
    cs_net_paid               number(7,2),
    cs_net_paid_inc_tax       number(7,2),
    cs_net_paid_inc_ship      number(7,2),
    cs_net_paid_inc_ship_tax  number(7,2),
    cs_net_profit             number(7,2),
    primary key (cs_item_sk, cs_order_number)
);

-- Store_sales table with CORRECT 23 columns (matching official TPC-DS spec)
create table store_sales
(
    ss_sold_date_sk           number,
    ss_sold_time_sk           number,
    ss_item_sk                number                not null,
    ss_customer_sk            number,
    ss_cdemo_sk               number,
    ss_hdemo_sk               number,
    ss_addr_sk                number,
    ss_store_sk               number,
    ss_promo_sk               number,
    ss_ticket_number          number                not null,
    ss_quantity               number,
    ss_wholesale_cost         number(7,2),
    ss_list_price             number(7,2),
    ss_sales_price            number(7,2),
    ss_ext_discount_amt       number(7,2),
    ss_ext_sales_price        number(7,2),
    ss_ext_wholesale_cost     number(7,2),
    ss_ext_list_price         number(7,2),
    ss_ext_tax                number(7,2),
    ss_coupon_amt             number(7,2),
    ss_net_paid               number(7,2),
    ss_net_paid_inc_tax       number(7,2),
    ss_net_profit             number(7,2),
    primary key (ss_item_sk, ss_ticket_number)
);

-- Add table and column statistics gathering after schema creation
BEGIN
    DBMS_STATS.GATHER_SCHEMA_STATS(
        ownname => USER,
        estimate_percent => DBMS_STATS.AUTO_SAMPLE_SIZE,
        method_opt => 'FOR ALL COLUMNS SIZE AUTO',
        degree => 4
    );
END;
/
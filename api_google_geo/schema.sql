-- api_geo 数据库初始化脚本
-- 执行前请先创建数据库: CREATE DATABASE api_geo CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE api_geo;

CREATE TABLE IF NOT EXISTS api_token (
    id          BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    token       VARCHAR(64)  NOT NULL UNIQUE COMMENT 'API Token 值',
    name        VARCHAR(100)          COMMENT 'Token 名称/备注',
    expired_at  DATETIME     NOT NULL COMMENT 'Token 过期时间',
    is_active   TINYINT      NOT NULL DEFAULT 1 COMMENT '1=启用 0=禁用',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_token (token)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API Token 管理';

CREATE TABLE IF NOT EXISTS api_request_log (
    id                       BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    token_id                 BIGINT UNSIGNED NOT NULL COMMENT '关联的 token.id',
    token                    VARCHAR(64)     NOT NULL COMMENT '请求时使用的 token（冗余存储）',
    request_ip               VARCHAR(45)              COMMENT '请求方 IP',
    request_lat              DECIMAL(10,7)   NOT NULL COMMENT '请求纬度',
    request_lon              DECIMAL(10,7)   NOT NULL COMMENT '请求经度',
    google_status            VARCHAR(20)              COMMENT 'Google API status 字段',
    response_country         VARCHAR(100)             COMMENT '国家',
    response_province        VARCHAR(100)             COMMENT '省份/直辖市（原始文本）',
    response_district        VARCHAR(100)             COMMENT '市/区（原始文本）',
    response_route           VARCHAR(200)             COMMENT '乡镇/街道',
    response_street_number   VARCHAR(100)             COMMENT '街道/门牌号',
    response_formatted_addr  VARCHAR(500)             COMMENT '详细地址',
    response_postal_code     VARCHAR(20)              COMMENT '邮编',
    response_plus_code       VARCHAR(30)              COMMENT 'Plus Code',
    province_id              BIGINT UNSIGNED          COMMENT '匹配到的省份 area.id（level=2）',
    district_id              BIGINT UNSIGNED          COMMENT '匹配到的市/区 area.id（level=3）',
    status                   TINYINT         NOT NULL DEFAULT 1 COMMENT '0=失败 1=成功',
    error_message            TEXT                     COMMENT '失败时的错误信息',
    response_time_ms         INT UNSIGNED             COMMENT 'Google API 响应耗时（毫秒）',
    created_at               DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_token_id   (token_id),
    INDEX idx_token      (token),
    INDEX idx_created_at (created_at),
    INDEX idx_status     (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='API 请求日志';

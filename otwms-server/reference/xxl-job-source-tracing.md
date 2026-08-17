# XXL-JOB 到源码的定位方法

## 适用场景

XXL-JOB 日志只有 Java 异常，需要确认实际执行器、部署包、Bitbucket 仓库、Jenkins Job 和源码文件。

## 只读定位顺序

1. 从 `xxl_job_info` 确认任务名称、handler、路由、超时和重试配置。
2. 从 `xxl_job_log` 确认目标日志 ID、触发时间、执行器地址和回调状态。
3. 将执行器内网地址映射到当前 GCP 实例；实例组名称可能变化。
4. 在执行器读取 `/tmp/<date>/<log-id>.log` 的必要片段，提取完整异常链、Java 类和方法。
5. 在 Jenkins 工作区按类名查找源文件，并核对 Job 的 SCM URL、分支和 Git commit。
6. 对 Jenkins 构建产物与生产 JAR 计算 SHA-256；一致后才能确认源码映射。
7. 将调度问题、业务代码问题和数据库问题分层，不因最外层异常或服务器名称误判责任系统。

## 判定标准

只有以下信息同时匹配，才可声明“已定位生产源码”：

- handler 和执行器匹配目标任务。
- 异常类存在于候选仓库。
- Jenkins Job 的 SCM 指向该仓库和目标分支。
- Jenkins 产物与生产 JAR 校验值一致。

只找到类名或 Jenkins 工作区不能单独证明生产对应关系。

## 安全边界

- 不输出数据库密码、Jenkins credentials、Token 或完整 Java 启动参数。
- 不在 Jenkins 工作区或生产服务器直接编辑代码/JAR。
- 读取日志时隐藏业务标识，只保留数量、时间和错误类型。

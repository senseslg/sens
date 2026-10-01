# D2 制图子项目

用于集中保存本仓库的 D2 图表源码和导出文件。

## 当前状态

- D2：`v0.9.0`，已验证可运行。
- 本机：Apple Silicon（`arm64`）。
- Homebrew 已迁移到 Apple Silicon 默认前缀 `/opt/homebrew`；D2 二进制为原生 `arm64`。

## 基本用法

```bash
cd /Users/lingang/sens/d2
d2 input.d2 output.svg
```

图表源文件使用 `.d2`；需要保留导出结果时，优先使用 `.svg`。

## 下一步

- 按实际主题创建 D2 源文件。

# 续开发须知

读取 DEVELOPMENT_LOG.md、CONTRIBUTING.md 和 docs/VALIDATION.md 后开始增强。默认测试不得联网或修改 NAS。固件必须精确匹配，有证据方可 verified。发行契约与 discovery 镜像保持一致。

不要读取或输出 nas-session、密码、SID、原始 HAR。需要登录时请求用户通过隐藏输入完成。远程测试以当次已获授权范围为准，避免重复询问已有授权；先检查资源冲突，finally 清理本次创建的测试资源。发布包索引需明确用户指令。

改变代码后运行离线回归、Ruff 和相应构建/安装验证，记录关键决策、设备版本、测试结果与待办，不能把推测写成已实测。

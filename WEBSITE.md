# 观照 · 摄影课程网站

将本目录文件合并到 57cx/aesthetic-weekly 仓库根目录，保留原有 README、curriculum 和课程目录。Node.js 24，无第三方运行依赖。

运行 `npm test` 和 `npm run build`；用 `python -m http.server 8080 --directory dist` 本地预览。

构建时自动扫描真实日期目录、题材、照片和 PDF，并把导读与每张范例的点评写进页面。有 Markdown 原稿的日期直接用原稿；只有 PDF 的日期使用 `site-readings/` 里已抽出的正文。新的每日课程只要带上 `今日导读.md` 和各题材 `解读原稿.md`，构建就会自动显示，不必再抽 PDF。PDF 链接仍保留为下载。repository-tree.json 是本次读取的 44 期仓库结构快照，仅在没有本地课程目录时用于独立预览。新增课程后，main 推送触发 Pages 重新构建，不需要手动维护列表。它不负责生成每周摄影内容，也不会替代或重复创建既有周更任务。

照片和 PDF 从公开 GitHub main 读取，保留原文件及 PDF 中的作者与授权信息；浏览器需能连接 raw.githubusercontent.com。学习进度保存在 localStorage，只适用于当前浏览器，不跨设备。

GitHub Pages 的部署源需要设置为 GitHub Actions。首次部署依赖仓库的 Pages 与 Actions 权限；请以 Actions 成功结果为上线依据。

网站已通过本机 Git 推送到 main，提交 06fb2a8。connector 仍返回 403，但本机 Git 读写可用。GitHub Actions 的测试与构建已通过；首次部署在 configure-pages 步骤失败，因为仓库尚未启用 GitHub Pages。请进入仓库 Settings → Pages，将 Source 设为 GitHub Actions，再重新运行 Photography course website 工作流。尚未验证上线。

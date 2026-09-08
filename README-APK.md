# 笨鸟先飞 (Silly Bird First Fly) — Android 打包说明

## 一键打包（推荐：GitHub Actions 云端构建）

1. 把本目录推到你的 GitHub 仓库
2. 在仓库 **Settings → Pages** 或直接进 **Actions** 标签页
3. 触发 `.github/workflows/build-apk.yml` workflow（push 到 main / 手动 Run workflow 都行）
4. 等待 20~40 分钟（首次会下载 Android SDK + NDK + SDL2，约 3GB）
5. 在 workflow 跑完的 **Artifacts** 区域下载 `sillybird-debug-apk.zip`
6. 解压得到 `bin/sillybird-1.0-debug.apk`，传到手机点击安装（手机需开启「未知来源」）
7. 装好后桌面会多一个「笨鸟先飞」图标，打开就能玩

### 加速二次构建

GitHub Actions 会自动缓存 `~/.gradle` 和 `~/.buildozer`，第二次构建通常只要 5~10 分钟。

### 发布正式版

把 workflow 里的 `buildozer android debug` 改成 `buildozer android release`，再配置签名即可（参考 p4a 文档的 keystore 部分）。

---

## 打包目录结构（buildozer 必看）

```
flappy/
├── main.py               # 入口（p4a 调这个）
├── game.py               # 主游戏
├── assets.py             # 资源（程序化生成）
├── soundfx.py            # 音效（程序化生成 WAV）
├── buildozer.spec        # p4a 配置
├── .github/workflows/    # GitHub Actions
└── cache/                # 运行时生成（首次启动会重新合成音效）
```

`buildozer.spec` 的 `source.exclude_patterns` 已排除 `_regress.py` `download_packs.py` `make_shortcut.py` `launch.bat` 等桌面端工具，避免打进 APK。

---

## 触屏交互

- **点屏幕任意空白位置** = 拍翅跳跃
- **左下角 音** = 开关音效（拍翅/得分/换图/撞机/破纪录欢呼）
- **左下角 乐** = 开关背景电子乐
- **右下角 ‖** = 暂停 / 继续
- **右下角 ≡** = 回选皮肤菜单

ESC/M/P 键被右下角虚拟按钮取代，因为手机没有物理键盘。

---

## 兼容性

- Android 5.0 (API 21) 及以上
- 推荐 Android 8.0+ 体验更流畅
- 竖屏锁定，适配各种屏占比

## 已知问题 & 限制

- 首次启动会现场合成 WAV 音效（4 个文件约 80ms），后续启动有缓存秒开
- pygame 在某些 Android 设备上 mixer 音轨可能没声，需要设备支持 OpenSL ES
- 没用 NDK 自己编译过 SDL2，全部用 p4a 内置的预编译版本

## 桌面端使用

桌面端完全不受影响，继续双击 `笨鸟先飞.lnk` 或跑 `python game.py` 即可。

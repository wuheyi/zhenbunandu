# 朕不南渡

靖康危机政略模拟可玩切片。当前版本实现：

- 新局与本地 SQLite 存档。
- 首月急奏、召见、密令、拟旨、颁诏。
- 月末回奏、密令产证、第二回合殿前对质。
- 无 LLM key 也可使用确定性规则完整走通。

## 运行

后端：

```bash
PYTHONPATH=backend .venv/bin/uvicorn zhenbunandu.app:app --host 127.0.0.1 --port 8010
```

前端：

```bash
cd web
npm run dev
```

然后打开 `http://127.0.0.1:5173`。

## 验证

```bash
PYTHONPATH=backend .venv/bin/pytest -q
cd web && npm run build
```

自动跑局平衡检查：

```bash
PYTHONPATH=backend .venv/bin/python -m zhenbunandu.autoplay --output /tmp/zhenbunandu-balance
```

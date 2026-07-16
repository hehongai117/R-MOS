// e2e/global-setup.ts
export default async function globalSetup() {
  const url = 'http://localhost:8000/api/v1/health'
  try {
    const resp = await fetch(url)
    if (!resp.ok) throw new Error(`health ${resp.status}`)
  } catch (err) {
    throw new Error(
      `后端未就绪（${url}）：${err}\n` +
        '本地请先启动：cd r-mos-backend && source venv/bin/activate && python main.py\n' +
        'CI 由 e2e-browser-ci.yml 负责启动 uvicorn。',
    )
  }
}

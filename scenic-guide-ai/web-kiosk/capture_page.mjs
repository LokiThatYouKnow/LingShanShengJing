import { chromium } from 'playwright'

const browser = await chromium.launch({ headless: true })
const page = await browser.newPage()

const allLogs = []

page.on('console', msg => {
  allLogs.push(`[${msg.type().toUpperCase()}] ${msg.text()}`)
})

page.on('pageerror', err => {
  allLogs.push(`[PAGE_ERROR] ${err.stack || err.message}`)
})

// 拦截所有请求
const failedReqs = []
page.on('requestfailed', req => {
  failedReqs.push(`${req.url()} → ${req.failure()?.errorText}`)
})

// 注入脚本：在Vue挂载前监控
await page.addInitScript(() => {
  // 拦截console.error
  const origError = console.error.bind(console)
  console.error = (...args) => {
    origError(...args)
  }
  // 监听模块加载错误
  window.addEventListener('error', e => {
    if (e.filename) {
      console.error('SCRIPT_ERROR in', e.filename, 'line', e.lineno, ':', e.message)
    }
  }, true)
})

console.log('加载页面...')
try {
  await page.goto('http://localhost:5174', { waitUntil: 'domcontentloaded', timeout: 10000 })
} catch(e) {}

await page.waitForTimeout(6000)

// 检查 #app 内容
const appContent = await page.evaluate(() => {
  const app = document.getElementById('app')
  return {
    innerHTML: app?.innerHTML?.slice(0, 300) || '(空)',
    childCount: app?.children?.length || 0
  }
})

// 检查Vue是否挂载
const vueInfo = await page.evaluate(() => {
  const app = document.getElementById('app')
  return {
    hasVueInstance: !!app?.__vue_app__,
    hasChildren: app?.innerHTML?.length > 0
  }
})

console.log('\n====== 所有控制台日志 ======')
allLogs.forEach((l,i) => console.log(`[${i+1}] ${l}`))

console.log('\n====== #app 状态 ======')
console.log('子元素数量:', appContent.childCount)
console.log('innerHTML:', appContent.innerHTML)
console.log('Vue已挂载:', vueInfo.hasVueInstance)

console.log('\n====== 失败请求 ======')
failedReqs.forEach(r => console.log('  ✗', r))

await browser.close()

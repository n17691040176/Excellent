function refreshRem() {
  const width = Math.min(window.innerWidth, 540)
  document.documentElement.style.fontSize = `${width / 10}px`
}

refreshRem()
window.addEventListener('resize', refreshRem)

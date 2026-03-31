/**
 * Android WebView 初始化脚本
 * 解决 ES6 模块加载问题
 */

// 等待 DOM 加载完成
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Init] AI小说拆书系统启动...');
    
    // 检查必要的全局对象
    if (typeof StateManager === 'undefined') {
        console.error('[Init] StateManager 未加载');
        showError('系统初始化失败：状态管理器未加载');
        return;
    }
    
    if (typeof APIClient === 'undefined') {
        console.error('[Init] APIClient 未加载');
        showError('系统初始化失败：API客户端未加载');
        return;
    }
    
    if (typeof NovelPlatformApp === 'undefined') {
        console.error('[Init] NovelPlatformApp 未加载');
        showError('系统初始化失败：主应用未加载');
        return;
    }
    
    // 初始化应用
    try {
        window.app = new NovelPlatformApp();
        window.app.init();
        console.log('[Init] 应用初始化成功');
    } catch (error) {
        console.error('[Init] 应用初始化失败:', error);
        showError('系统初始化失败：' + error.message);
    }
});

// 显示错误信息
function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:#ef4444;color:white;padding:20px;border-radius:8px;max-width:80%;text-align:center;z-index:9999;';
    errorDiv.textContent = message;
    document.body.appendChild(errorDiv);
}

// 全局错误处理
window.addEventListener('error', function(e) {
    console.error('[Global Error]', e.error || e.message);
});

window.addEventListener('unhandledrejection', function(e) {
    console.error('[Unhandled Promise]', e.reason);
});

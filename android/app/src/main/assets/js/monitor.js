let monitorInterval = null;

document.addEventListener('DOMContentLoaded', () => {
    loadBooks();
    document.getElementById('bookSelect').addEventListener('change', (e) => {
        if (e.target.value) {
            startMonitoring(e.target.value);
        } else {
            stopMonitoring();
        }
    });
});

async function loadBooks() {
    try {
        const books = await apiCall('/api/books');
        const select = document.getElementById('bookSelect');
        select.innerHTML = books.length ? 
            books.map(b => `<option value="${b.id}">${b.name}</option>`).join('') :
            '<option value="">暂无处理中的书籍</option>';
    } catch (error) {
        console.error('加载书籍列表失败:', error);
    }
}

function startMonitoring(bookId) {
    stopMonitoring();
    updateMonitor(bookId);
    monitorInterval = setInterval(() => updateMonitor(bookId), 2000);
}

function stopMonitoring() {
    if (monitorInterval) {
        clearInterval(monitorInterval);
        monitorInterval = null;
    }
}

async function updateMonitor(bookId) {
    try {
        const status = await apiCall(`/api/books/${bookId}/status`);
        renderMonitor(status);
    } catch (error) {
        console.error('获取状态失败:', error);
    }
}

function renderMonitor(status) {
    const content = document.getElementById('monitorContent');
    const stages = [
        { key: 'chapter', name: '章纲提取', total: status.total_chapters },
        { key: 'rough', name: '粗纲生成', total: Math.ceil(status.total_chapters / 10) },
        { key: 'outline', name: '大纲生成', total: Math.ceil(status.total_chapters / 100) },
        { key: 'world', name: '世界纲生成', total: 1 }
    ];
    
    content.innerHTML = stages.map(stage => {
        const stageData = status[stage.key] || { completed: 0, errors: [] };
        const progress = (stageData.completed / stage.total * 100).toFixed(0);
        const statusClass = stageData.completed === stage.total ? 'completed' : 
                           stageData.errors.length ? 'error' : 'processing';
        
        return `
            <div class="process-stage">
                <div class="stage-header">
                    <h3 class="stage-title">${stage.name}</h3>
                    <span class="stage-status ${statusClass}">
                        ${statusClass === 'completed' ? '已完成' : 
                          statusClass === 'error' ? '有错误' : '处理中'}
                    </span>
                </div>
                <div class="stage-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progress}%"></div>
                    </div>
                    <div class="progress-text">${stageData.completed} / ${stage.total}</div>
                </div>
                ${stageData.errors.length ? `
                    <div class="error-message">
                        错误: ${stageData.errors.join('; ')}
                    </div>
                ` : ''}
            </div>
        `;
    }).join('');
}

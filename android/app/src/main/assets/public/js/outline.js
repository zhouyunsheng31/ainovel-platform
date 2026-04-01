document.addEventListener('DOMContentLoaded', () => {
    loadCompletedBooks();
    document.getElementById('outlineBookSelect').addEventListener('change', (e) => {
        if (e.target.value) loadOutline(e.target.value);
    });
});

async function loadCompletedBooks() {
    try {
        const books = await apiCall('/api/books?status=completed');
        const select = document.getElementById('outlineBookSelect');
        select.innerHTML = books.length ?
            books.map(b => `<option value="${b.id}">${b.name}</option>`).join('') :
            '<option value="">暂无已完成的书籍</option>';
    } catch (error) {
        console.error('加载书籍失败:', error);
    }
}

async function loadOutline(bookId) {
    try {
        const outline = await apiCall(`/api/books/${bookId}/outline`);
        renderOutlineTree(outline);
    } catch (error) {
        showToast('加载纲要失败', 'error');
    }
}

function renderOutlineTree(data) {
    const content = document.getElementById('outlineContent');
    content.innerHTML = `
        <div class="outline-tree">
            ${renderNode(data.world, 'world')}
        </div>
    `;
}

function renderNode(node, type) {
    const children = node.children || [];
    const childType = type === 'world' ? 'outline' : 
                     type === 'outline' ? 'rough' : 'chapter';
    
    return `
        <div class="tree-node">
            <div class="node-card ${type}" onclick="showDetail(${JSON.stringify(node).replace(/"/g, '"')})">
                <div class="node-title">${node.title}</div>
                <div class="node-summary">${node.summary || ''}</div>
            </div>
            ${children.length ? `
                <div class="node-children">
                    ${children.map(c => renderNode(c, childType)).join('')}
                </div>
            ` : ''}
        </div>
    `;
}

function showDetail(node) {
    const modal = document.createElement('div');
    modal.className = 'outline-modal';
    modal.innerHTML = `
        <div class="modal-content">
            <div class="modal-header">
                <h2 class="modal-title">${node.title}</h2>
                <div class="modal-actions">
                    <button class="btn-icon" onclick="copyContent(${JSON.stringify(node).replace(/"/g, '"')})">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                        </svg>
                    </button>
                    <button class="btn-icon" onclick="this.closest('.outline-modal').remove()">
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            </div>
            <div class="modal-body">
                ${Object.entries(node).filter(([k]) => k !== 'children' && k !== 'title')
                    .map(([k, v]) => `
                        <div class="outline-section">
                            <div class="section-title">${k}</div>
                            <div class="section-content">${typeof v === 'object' ? JSON.stringify(v, null, 2) : v}</div>
                        </div>
                    `).join('')}
            </div>
        </div>
    `;
    document.body.appendChild(modal);modal.addEventListener('click', (e) => {
        if (e.target === modal) modal.remove();
    });
}

function copyContent(node) {
    const text = JSON.stringify(node, null, 2);
    navigator.clipboard.writeText(text).then(() => {
        showToast('已复制到剪贴板', 'success');
    });
}

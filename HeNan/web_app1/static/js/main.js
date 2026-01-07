// API基础URL
const API_BASE = '/api';

// 当前页码
let currentPage = 1;
let pageSize = 10;
let totalPages = 1;
let currentDramaName = '';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    loadDramaList();
});

// 显示页面
function showPage(pageId) {
    // 隐藏所有页面
    document.querySelectorAll('.page').forEach(page => {
        page.classList.remove('active');
    });
    
    // 显示目标页面
    const targetPage = document.getElementById(pageId + '-page');
    if (targetPage) {
        targetPage.classList.add('active');
    }
    
    // 更新导航状态
    document.querySelectorAll('.nav-item-btn').forEach(btn => {
        btn.classList.remove('bg-blue-600', 'text-white', 'shadow-md');
        btn.classList.add('text-slate-400', 'hover:bg-slate-800', 'hover:text-white');
    });
    
    const activeBtn = document.getElementById('nav-' + pageId);
    if (activeBtn) {
        activeBtn.classList.remove('text-slate-400', 'hover:bg-slate-800', 'hover:text-white');
        activeBtn.classList.add('bg-blue-600', 'text-white', 'shadow-md');
    }
    
    // 更新header标题
    const headerTitle = document.getElementById('header-title');
    if (headerTitle) {
        headerTitle.textContent = pageId === 'drama-list' ? '剧集管理中心' : '剧集查询';
    }
    
    // 如果是剧集列表页面，加载数据
    if (pageId === 'drama-list') {
        loadDramaList();
    }
}

// 加载剧集列表
async function loadDramaList(page = 1) {
    currentPage = page;
    const keyword = document.getElementById('search-input')?.value || '';
    
    try {
        const response = await fetch(`${API_BASE}/dramas?keyword=${encodeURIComponent(keyword)}&page=${page}&page_size=${pageSize}`);
        const result = await response.json();
        
        if (result.code === 200) {
            renderDramaTable(result.data.list);
            renderPagination(result.data);
        } else {
            showError('加载数据失败：' + result.message);
        }
    } catch (error) {
        showError('加载数据失败：' + error.message);
    }
}

// 渲染剧集表格
function renderDramaTable(dramas) {
    const tbody = document.getElementById('drama-table-body');
    
    if (!dramas || dramas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-8 text-center text-slate-500">暂无数据</td></tr>';
        return;
    }
    
    tbody.innerHTML = dramas.map(drama => {
        const props = drama.dynamic_properties || {};
        return `
            <tr class="hover:bg-slate-50 transition-colors group">
                <td class="px-6 py-4 text-slate-900">${drama.drama_id}</td>
                <td class="px-6 py-4">
                    <div class="font-medium text-slate-900">${drama.drama_name}</div>
                </td>
                <td class="px-6 py-4 text-slate-600 hidden sm:table-cell">${props['内容类型'] || '-'}</td>
                <td class="px-6 py-4 text-slate-600 hidden sm:table-cell">${props['总集数'] || 0}</td>
                <td class="px-6 py-4 hidden sm:table-cell">
                    ${props['评分'] ? `<span class="flex items-center gap-1 text-orange-500 font-medium">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none">
                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                        </svg>
                        ${props['评分']}
                    </span>` : '-'}
                </td>
                <td class="px-6 py-4 text-right">
                    <button onclick="viewDramaDetail(${drama.drama_id}, '${drama.drama_name.replace(/'/g, "\\'")}')" 
                        class="text-blue-600 hover:text-blue-700 font-medium text-sm inline-flex items-center gap-1 bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg transition-all">
                        查看详情
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="m9 18 6-6-6-6"/>
                        </svg>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// 渲染分页
function renderPagination(data) {
    totalPages = data.total_pages;
    const pagination = document.getElementById('pagination');
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    pagination.innerHTML = `
        <button ${currentPage === 1 ? 'disabled' : ''} 
            onclick="loadDramaList(${currentPage - 1})"
            class="px-4 py-2 border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            上一页
        </button>
        <span class="text-sm text-slate-600 mx-4">第 ${currentPage} / ${totalPages} 页，共 ${data.total} 条</span>
        <button ${currentPage === totalPages ? 'disabled' : ''} 
            onclick="loadDramaList(${currentPage + 1})"
            class="px-4 py-2 border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            下一页
        </button>
    `;
}

// 搜索剧集
function searchDramas() {
    loadDramaList(1);
}

// 查看剧集详情
async function viewDramaDetail(dramaId, dramaName) {
    currentDramaName = dramaName;
    
    try {
        // 获取剧集详情
        const response = await fetch(`${API_BASE}/dramas/${dramaId}`);
        const result = await response.json();
        
        if (result.code === 200) {
            const header = result.data;
            
            // 获取子集列表
            const episodesResponse = await fetch(`${API_BASE}/dramas/${dramaId}/episodes`);
            const episodesResult = await episodesResponse.json();
            const episodes = episodesResult.code === 200 ? episodesResult.data : [];
            
            showDramaDetailModal(header, episodes);
        } else {
            showError('获取详情失败：' + result.message);
        }
    } catch (error) {
        showError('获取详情失败：' + error.message);
    }
}

// 显示剧集详情模态框
function showDramaDetailModal(header, episodes) {
    const modal = document.getElementById('detail-modal');
    const modalBody = document.getElementById('modal-body');
    const modalTitle = document.getElementById('modal-title');
    
    modalTitle.textContent = header['剧集名称'] || '剧集详情';
    
    // 构建详情HTML
    let html = '<div class="space-y-6">';
    html += '<div>';
    html += '<h3 class="text-lg font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-200">剧集基本信息</h3>';
    html += '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">';
    
    const headerFields = [
        { label: '剧集ID', key: '剧头id' },
        { label: '剧集名称', key: '剧集名称' },
        { label: '作者列表', key: '作者列表' },
        { label: '清晰度', key: '清晰度' },
        { label: '语言', key: '语言' },
        { label: '主演', key: '主演' },
        { label: '内容类型', key: '内容类型' },
        { label: '上映年份', key: '上映年份' },
        { label: '关键字', key: '关键字' },
        { label: '评分', key: '评分' },
        { label: '推荐语', key: '推荐语' },
        { label: '总集数', key: '总集数' },
        { label: '产品分类', key: '产品分类' },
        { label: '版权', key: '版权' },
        { label: '二级分类', key: '二级分类' }
    ];
    
    headerFields.forEach(field => {
        const value = header[field.key] !== null && header[field.key] !== undefined ? header[field.key] : '-';
        html += `
            <div class="flex flex-col">
                <span class="text-xs text-slate-500 mb-1">${field.label}</span>
                <span class="text-sm text-slate-900 font-medium">${value}</span>
            </div>
        `;
    });
    
    html += '</div>';
    
    // 描述信息
    if (header['描述']) {
        html += '<div class="mt-6">';
        html += '<span class="text-xs text-slate-500 mb-2 block">描述</span>';
        html += `<p class="text-sm text-slate-700 leading-relaxed">${header['描述']}</p>`;
        html += '</div>';
    }
    
    html += '</div>';
    
    // 子集信息
    if (episodes && episodes.length > 0) {
        html += '<div>';
        html += '<h3 class="text-lg font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-200">子集信息 (' + episodes.length + ' 集)</h3>';
        html += '<div class="overflow-x-auto">';
        html += '<table class="w-full text-left border-collapse">';
        html += '<thead>';
        html += '<tr class="bg-slate-50 border-b border-slate-200">';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">子集ID</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">节目名称</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">集数</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">媒体拉取地址</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">媒体类型</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">编码格式</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">时长</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">文件大小</th>';
        html += '</tr>';
        html += '</thead>';
        html += '<tbody class="divide-y divide-slate-100">';
        
        episodes.forEach(episode => {
            html += '<tr class="hover:bg-slate-50">';
            html += `<td class="px-4 py-3 text-slate-900">${episode['子集id']}</td>`;
            html += `<td class="px-4 py-3 text-slate-900">${episode['节目名称']}</td>`;
            html += `<td class="px-4 py-3 text-slate-600">${episode['集数']}</td>`;
            html += `<td class="px-4 py-3 text-slate-600 max-w-xs truncate" title="${episode['媒体拉取地址'] || ''}">${episode['媒体拉取地址'] || '-'}</td>`;
            html += `<td class="px-4 py-3 text-slate-600">${episode['媒体类型'] || '-'}</td>`;
            html += `<td class="px-4 py-3 text-slate-600">${episode['编码格式'] || '-'}</td>`;
            html += `<td class="px-4 py-3 text-slate-600">${episode['时长'] || '-'}</td>`;
            html += `<td class="px-4 py-3 text-slate-600">${episode['文件大小'] || '-'}</td>`;
            html += '</tr>';
        });
        
        html += '</tbody>';
        html += '</table>';
        html += '</div>';
        html += '</div>';
    }
    
    html += '</div>';
    
    modalBody.innerHTML = html;
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

// 关闭模态框
function closeModal() {
    const modal = document.getElementById('detail-modal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

// 点击模态框外部关闭
document.addEventListener('click', function(event) {
    const modal = document.getElementById('detail-modal');
    if (event.target === modal) {
        closeModal();
    }
});

// 根据剧集名称搜索
async function searchDramaByName() {
    const dramaName = document.getElementById('drama-name-input').value.trim();
    
    if (!dramaName) {
        showError('请输入剧集名称');
        return;
    }
    
    const resultDiv = document.getElementById('search-result');
    resultDiv.innerHTML = '<div class="text-center text-slate-500 py-12">查询中...</div>';
    
    try {
        const response = await fetch(`${API_BASE}/dramas/search/${encodeURIComponent(dramaName)}`);
        const result = await response.json();
        
        if (result.code === 200 && result.data) {
            const { header, episodes } = result.data;
            showSearchResult(header, episodes);
        } else {
            resultDiv.innerHTML = `<div class="text-center text-slate-500 py-12">${result.message || '未找到该剧集'}</div>`;
        }
    } catch (error) {
        showError('查询失败：' + error.message);
        resultDiv.innerHTML = `<div class="text-center text-red-500 py-12">查询失败：${error.message}</div>`;
    }
}

// 显示搜索结果
function showSearchResult(header, episodes) {
    const resultDiv = document.getElementById('search-result');
    currentDramaName = header['剧集名称'];
    
    let html = '<div class="space-y-6">';
    html += '<div>';
    html += '<h3 class="text-lg font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-200">剧集基本信息</h3>';
    html += '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">';
    
    const headerFields = [
        { label: '剧集ID', key: '剧头id' },
        { label: '剧集名称', key: '剧集名称' },
        { label: '作者列表', key: '作者列表' },
        { label: '清晰度', key: '清晰度' },
        { label: '语言', key: '语言' },
        { label: '主演', key: '主演' },
        { label: '内容类型', key: '内容类型' },
        { label: '上映年份', key: '上映年份' },
        { label: '关键字', key: '关键字' },
        { label: '评分', key: '评分' },
        { label: '推荐语', key: '推荐语' },
        { label: '总集数', key: '总集数' },
        { label: '产品分类', key: '产品分类' },
        { label: '版权', key: '版权' },
        { label: '二级分类', key: '二级分类' }
    ];
    
    headerFields.forEach(field => {
        const value = header[field.key] !== null && header[field.key] !== undefined ? header[field.key] : '-';
        html += `
            <div class="flex flex-col">
                <span class="text-xs text-slate-500 mb-1">${field.label}</span>
                <span class="text-sm text-slate-900 font-medium">${value}</span>
            </div>
        `;
    });
    
    html += '</div>';
    
    if (header['描述']) {
        html += '<div class="mt-6">';
        html += '<span class="text-xs text-slate-500 mb-2 block">描述</span>';
        html += `<p class="text-sm text-slate-700 leading-relaxed">${header['描述']}</p>`;
        html += '</div>';
    }
    
    html += '</div>';
    
    // 子集信息
    if (episodes && episodes.length > 0) {
        html += '<div>';
        html += '<h3 class="text-lg font-semibold text-slate-900 mb-4 pb-2 border-b border-slate-200">子集信息 (' + episodes.length + ' 集)</h3>';
        html += '<div class="overflow-x-auto">';
        html += '<table class="w-full text-left border-collapse">';
        html += '<thead>';
        html += '<tr class="bg-slate-50 border-b border-slate-200">';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">子集ID</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">节目名称</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">集数</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">媒体拉取地址</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">媒体类型</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">编码格式</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">时长</th>';
        html += '<th class="px-4 py-3 text-slate-500 font-semibold text-sm">文件大小</th>';
        html += '</tr>';
        html += '</thead>';
        html += '<tbody class="divide-y divide-slate-100">';
        
        episodes.forEach(episode => {
            html += '<tr class="hover:bg-slate-50">';
            html += `<td class="px-4 py-3 text-slate-900">${episode['子集id']}</td>`;
            html += `<td class="px-4 py-3 text-slate-900">${episode['节目名称']}</td>`;
            html += `<td class="px-4 py-3 text-slate-600">${episode['集数']}</td>`;
            html += `<td class="px-4 py-3 text-slate-600 max-w-xs truncate" title="${episode['媒体拉取地址'] || ''}">${episode['媒体拉取地址'] || '-'}</td>`;
            html += `<td class="px-4 py-3 text-slate-600">${episode['媒体类型'] || '-'}</td>`;
            html += `<td class="px-4 py-3 text-slate-600">${episode['编码格式'] || '-'}</td>`;
            html += `<td class="px-4 py-3 text-slate-600">${episode['时长'] || '-'}</td>`;
            html += `<td class="px-4 py-3 text-slate-600">${episode['文件大小'] || '-'}</td>`;
            html += '</tr>';
        });
        
        html += '</tbody>';
        html += '</table>';
        html += '</div>';
        html += '</div>';
    }
    
    // 添加导出按钮
    html += '<div class="mt-6 text-center">';
    html += `<button onclick="exportDrama()" 
        class="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg transition-colors font-medium shadow-md shadow-green-600/20">
        导出Excel
    </button>`;
    html += '</div>';
    
    html += '</div>';
    
    resultDiv.innerHTML = html;
}

// 导出Excel
async function exportDrama() {
    if (!currentDramaName) {
        showError('请先选择或查询一个剧集');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/export/${encodeURIComponent(currentDramaName)}`);
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `${currentDramaName}_数据.xlsx`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            showSuccess('导出成功！');
        } else {
            const result = await response.json();
            showError('导出失败：' + (result.detail || '未知错误'));
        }
    } catch (error) {
        showError('导出失败：' + error.message);
    }
}

// 显示错误消息
function showError(message) {
    alert('错误：' + message);
}

// 显示成功消息
function showSuccess(message) {
    alert('成功：' + message);
}

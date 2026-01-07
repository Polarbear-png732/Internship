// API基础URL
const API_BASE = '/api';

// 当前页码
let currentPage = 1;
let pageSize = 10;
let totalPages = 1;
let currentDramaName = '';
let currentCustomerId = null;
let currentCustomerName = '';

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    loadCustomerList();
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
        if (pageId === 'customer-list') {
            headerTitle.textContent = '用户管理中心';
        } else if (pageId === 'drama-list') {
            headerTitle.textContent = currentCustomerName ? `${currentCustomerName} - 剧集管理` : '剧集管理中心';
        } else if (pageId === 'placeholder') {
            headerTitle.textContent = '等待增加的模块';
        }
    }
    
    // 如果是用户列表页面，加载数据
    if (pageId === 'customer-list') {
        loadCustomerList();
    }
}

// 加载用户列表
async function loadCustomerList() {
    try {
        const response = await fetch(`${API_BASE}/customers`);
        const result = await response.json();
        
        if (result.code === 200) {
            renderCustomerTable(result.data);
        } else {
            showError('加载用户列表失败：' + result.message);
        }
    } catch (error) {
        showError('加载用户列表失败：' + error.message);
    }
}

// 渲染用户表格
function renderCustomerTable(customers) {
    const tbody = document.getElementById('customer-table-body');
    
    if (!customers || customers.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-8 text-center text-slate-500">暂无用户数据</td></tr>';
        return;
    }
    
    // 生成随机渐变色
    const gradientColors = [
        'from-blue-500 to-cyan-500',
        'from-purple-500 to-pink-500',
        'from-orange-500 to-red-500',
        'from-green-500 to-emerald-500',
        'from-indigo-500 to-blue-500',
        'from-pink-500 to-rose-500',
        'from-yellow-500 to-orange-500',
        'from-teal-500 to-cyan-500'
    ];
    
    tbody.innerHTML = customers.map((customer, index) => {
        const gradient = gradientColors[index % gradientColors.length];
        return `
            <tr class="hover:bg-gradient-to-r hover:from-blue-50/50 hover:to-indigo-50/50 transition-all duration-200 group border-b border-slate-100">
                <td class="px-6 py-5">
                    <div class="flex items-center gap-4">
                        <div class="w-12 h-12 rounded-xl bg-gradient-to-br ${gradient} flex items-center justify-center text-white font-bold text-lg shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
                            ${customer.customer_name.charAt(0)}
                        </div>
                        <div>
                            <div class="font-semibold text-slate-900 text-base flex items-center gap-2">
                                ${customer.customer_name}
                                <span class="text-xs font-normal text-slate-400">ID: ${customer.customer_id}</span>
                            </div>
                            ${customer.remark ? `<div class="text-sm text-slate-500 mt-1 flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-slate-400">
                                    <path d="M14 9V5a3 3 0 0 0-6 0v4"/>
                                    <rect width="20" height="14" x="2" y="11" rx="2" ry="2"/>
                                </svg>
                                ${customer.remark}
                            </div>` : ''}
                        </div>
                    </div>
                </td>
                <td class="px-6 py-5 text-slate-600 hidden sm:table-cell">
                    <div class="flex items-center gap-2">
                        <span class="px-3 py-1 bg-slate-100 rounded-md text-sm font-mono text-slate-700 border border-slate-200">
                            ${customer.customer_code || '-'}
                        </span>
                    </div>
                </td>
                <td class="px-6 py-5 hidden sm:table-cell">
                    <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-semibold bg-gradient-to-r from-blue-500 to-indigo-500 text-white shadow-sm shadow-blue-500/30">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>
                            <path d="M7 3v18"/>
                            <path d="M3 7.5h4"/>
                            <path d="M3 12h18"/>
                            <path d="M3 16.5h4"/>
                            <path d="M17 3v18"/>
                            <path d="M17 7.5h4"/>
                            <path d="M17 16.5h4"/>
                        </svg>
                        ${customer.drama_count || 0} 部
                    </span>
                </td>
                <td class="px-6 py-5 text-right">
                    <button onclick="viewCustomerDramas(${customer.customer_id}, '${customer.customer_name.replace(/'/g, "\\'")}')" 
                        class="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-medium text-sm rounded-lg transition-all shadow-md shadow-blue-600/20 hover:shadow-lg hover:shadow-blue-600/30 hover:scale-105">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M5 12h14"/>
                            <path d="m12 5 7 7-7 7"/>
                        </svg>
                        管理剧集
                    </button>
                </td>
            </tr>
        `;
    }).join('');
}

// 查看用户的剧集列表
function viewCustomerDramas(customerId, customerName) {
    currentCustomerId = customerId;
    currentCustomerName = customerName;
    
    // 切换到剧集列表页面
    showPage('drama-list');
    
    // 更新标题
    const titleEl = document.getElementById('drama-list-title');
    const subtitleEl = document.getElementById('drama-list-subtitle');
    if (titleEl) {
        titleEl.textContent = `${customerName} 的剧集库`;
    }
    if (subtitleEl) {
        subtitleEl.textContent = `共发布剧集，点击查看详细信息`;
    }
    
    // 加载该用户的剧集列表
    loadDramaList(1);
}

// 返回用户列表
function backToCustomerList() {
    currentCustomerId = null;
    currentCustomerName = '';
    showPage('customer-list');
}

// 加载剧集列表
async function loadDramaList(page = 1) {
    currentPage = page;
    const keyword = document.getElementById('search-input')?.value || '';
    
    try {
        let url = `${API_BASE}/dramas?page=${page}&page_size=${pageSize}`;
        if (currentCustomerId) {
            url += `&customer_id=${currentCustomerId}`;
        }
        if (keyword) {
            url += `&keyword=${encodeURIComponent(keyword)}`;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.code === 200) {
            renderDramaTable(result.data.list);
            renderPagination(result.data);
            
            // 更新副标题显示剧集数量
            const subtitleEl = document.getElementById('drama-list-subtitle');
            if (subtitleEl) {
                subtitleEl.textContent = `共 ${result.data.total} 部剧集`;
            }
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
        tbody.innerHTML = '<tr><td colspan="6" class="px-6 py-12 text-center text-slate-500"><div class="flex flex-col items-center gap-3"><svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-slate-300"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/></svg><span class="text-base">暂无剧集数据</span></div></td></tr>';
        return;
    }
    
    tbody.innerHTML = dramas.map((drama, index) => {
        const props = drama.dynamic_properties || {};
        const contentType = props['内容类型'] || '-';
        const rating = props['评分'] || 0;
        const totalEpisodes = props['总集数'] || 0;
        
        const rowClass = index % 2 === 0 ? 'bg-white' : 'bg-slate-50/30';
        return `
            <tr class="${rowClass} hover:bg-blue-50/50 transition-all duration-200 border-b border-slate-100 group">
                <td class="px-6 py-4">
                    <div class="flex items-center gap-2">
                        <div class="w-8 h-8 rounded-md bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center text-white font-bold text-sm shadow-sm">
                            ${drama.drama_id}
                        </div>
                    </div>
                </td>
                <td class="px-6 py-4">
                    <div class="font-semibold text-slate-900 text-base">${drama.drama_name}</div>
                    ${props['推荐语'] ? `<div class="text-xs text-slate-500 mt-1.5 flex items-center gap-1.5">
                        <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-slate-400">
                            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                        </svg>
                        <span class="italic">${props['推荐语']}</span>
                    </div>` : ''}
                </td>
                <td class="px-6 py-4 hidden sm:table-cell">
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-sm font-medium">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-slate-500">
                            <rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>
                        </svg>
                        ${contentType}
                    </span>
                </td>
                <td class="px-6 py-4 hidden sm:table-cell">
                    <span class="inline-flex items-center gap-1.5 text-slate-700 font-medium">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-500">
                            <line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>
                        </svg>
                        ${totalEpisodes} 集
                    </span>
                </td>
                <td class="px-6 py-4 hidden sm:table-cell">
                    ${rating ? `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-gradient-to-r from-orange-100 to-amber-100 text-orange-700 font-semibold text-sm border border-orange-200">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none" class="text-orange-500">
                            <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
                        </svg>
                        ${rating}
                    </span>` : '<span class="text-slate-400">-</span>'}
                </td>
                <td class="px-6 py-4 text-right">
                    <button onclick="viewDramaDetail(${drama.drama_id}, '${drama.drama_name.replace(/'/g, "\\'")}')" 
                        class="text-blue-600 hover:text-blue-700 font-semibold text-sm inline-flex items-center gap-1.5 bg-blue-50 hover:bg-blue-100 border border-blue-200 hover:border-blue-300 px-3.5 py-2 rounded-lg transition-all shadow-sm hover:shadow-md group-hover:scale-105">
                        查看详情
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
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
            
            showDramaDetailPage(header, episodes);
        } else {
            showError('获取详情失败：' + result.message);
        }
    } catch (error) {
        showError('获取详情失败：' + error.message);
    }
}

// 显示剧集详情页面
function showDramaDetailPage(header, episodes) {
    // 隐藏列表页面，显示详情页面
    document.getElementById('drama-list-page').classList.remove('active');
    document.getElementById('detail-page').classList.add('active');
    
    // 更新标题
    const detailTitle = document.getElementById('detail-title');
    detailTitle.textContent = header['剧集名称'] || '剧集详情';
    
    // 更新header标题
    const headerTitle = document.getElementById('header-title');
    if (headerTitle) {
        headerTitle.textContent = header['剧集名称'] || '剧集详情';
    }
    
    const detailBody = document.getElementById('detail-body');
    
    // 构建详情HTML
    let html = '<div class="space-y-6">';
    
    // 剧集基本信息卡片
    html += '<div class="bg-gradient-to-br from-white to-slate-50 border border-slate-200 rounded-xl p-6 shadow-lg">';
    html += '<div class="flex items-center gap-3 mb-6 pb-4 border-b border-slate-200">';
    html += '<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-xl shadow-lg">';
    html += (header['剧集名称'] ? header['剧集名称'].charAt(0) : '剧');
    html += '</div>';
    html += '<div><h3 class="text-xl font-bold text-slate-900 flex items-center gap-2"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-purple-600"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/></svg>剧集基本信息</h3><p class="text-sm text-slate-500 mt-1">查看完整的剧集详细信息</p></div>';
    html += '</div>';
    html += '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">';
    
    const headerFields = [
        { label: '剧集ID', key: '剧头id', icon: 'hash', color: 'blue' },
        { label: '剧集名称', key: '剧集名称', icon: 'film', color: 'purple' },
        { label: '作者列表', key: '作者列表', icon: 'users', color: 'indigo' },
        { label: '清晰度', key: '清晰度', icon: 'monitor', color: 'cyan' },
        { label: '语言', key: '语言', icon: 'globe', color: 'teal' },
        { label: '主演', key: '主演', icon: 'star', color: 'amber' },
        { label: '内容类型', key: '内容类型', icon: 'grid', color: 'pink' },
        { label: '上映年份', key: '上映年份', icon: 'calendar', color: 'rose' },
        { label: '关键字', key: '关键字', icon: 'tag', color: 'violet' },
        { label: '评分', key: '评分', icon: 'star', color: 'yellow' },
        { label: '推荐语', key: '推荐语', icon: 'message', color: 'sky' },
        { label: '总集数', key: '总集数', icon: 'list', color: 'emerald' },
        { label: '产品分类', key: '产品分类', icon: 'package', color: 'orange' },
        { label: '版权', key: '版权', icon: 'shield', color: 'green' },
        { label: '二级分类', key: '二级分类', icon: 'layers', color: 'slate' }
    ];
    
    const iconMap = {
        'hash': '<line x1="4" x2="20" y1="9" y2="9"/><line x1="4" x2="20" y1="15" y2="15"/><line x1="10" x2="8" y1="3" y2="21"/><line x1="16" x2="14" y1="3" y2="21"/>',
        'film': '<rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/>',
        'users': '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>',
        'monitor': '<rect width="20" height="14" x="2" y="3" rx="2"/><line x1="8" x2="16" y1="21" y2="21"/><line x1="12" x2="12" y1="17" y2="21"/>',
        'globe': '<circle cx="12" cy="12" r="10"/><line x1="2" x2="22" y1="12" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>',
        'star': '<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>',
        'grid': '<rect width="7" height="7" x="3" y="3" rx="1"/><rect width="7" height="7" x="14" y="3" rx="1"/><rect width="7" height="7" x="14" y="14" rx="1"/><rect width="7" height="7" x="3" y="14" rx="1"/>',
        'calendar': '<rect width="18" height="18" x="3" y="4" rx="2" ry="2"/><line x1="16" x2="16" y1="2" y2="6"/><line x1="8" x2="8" y1="2" y2="6"/><line x1="3" x2="21" y1="10" y2="10"/>',
        'tag': '<path d="M12.586 2.586A2 2 0 0 0 11.172 2H4a2 2 0 0 0-2 2v7.172a2 2 0 0 0 .586 1.414l8.414 8.414a2 2 0 0 0 2.828 0l7.172-7.172a2 2 0 0 0 0-2.828Z"/><circle cx="7.5" cy="7.5" r=".5" fill="currentColor"/>',
        'message': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
        'list': '<line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>',
        'package': '<path d="m7.5 4.27 9 5.15"/><path d="M21 10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/><path d="M3.29 7 12 12l8.71-5"/><path d="M12 22V12"/>',
        'shield': '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/>',
        'layers': '<path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/>'
    };
    
    const colorMap = {
        'blue': 'from-blue-500 to-cyan-500',
        'purple': 'from-purple-500 to-pink-500',
        'indigo': 'from-indigo-500 to-blue-500',
        'cyan': 'from-cyan-500 to-teal-500',
        'teal': 'from-teal-500 to-emerald-500',
        'amber': 'from-amber-500 to-orange-500',
        'pink': 'from-pink-500 to-rose-500',
        'rose': 'from-rose-500 to-red-500',
        'violet': 'from-violet-500 to-purple-500',
        'yellow': 'from-yellow-400 to-orange-500',
        'sky': 'from-sky-500 to-blue-500',
        'emerald': 'from-emerald-500 to-green-500',
        'orange': 'from-orange-500 to-red-500',
        'green': 'from-green-500 to-emerald-500',
        'slate': 'from-slate-500 to-slate-600'
    };
    
    headerFields.forEach(field => {
        const value = header[field.key] !== null && header[field.key] !== undefined ? header[field.key] : '-';
        const gradient = colorMap[field.color] || 'from-slate-500 to-slate-600';
        const iconPath = iconMap[field.icon] || '';
        const isSpecial = field.key === '评分' && value !== '-';
        
        html += '<div class="group relative bg-white border border-slate-200 rounded-lg p-4 hover:shadow-md transition-all hover:border-purple-300">';
        html += '<div class="flex items-start gap-3">';
        html += '<div class="w-10 h-10 rounded-lg bg-gradient-to-br ' + gradient + ' flex items-center justify-center text-white shadow-sm group-hover:scale-110 transition-transform flex-shrink-0">';
        html += '<svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' + iconPath + '</svg>';
        html += '</div>';
        html += '<div class="flex-1 min-w-0">';
        html += '<div class="text-xs font-medium text-slate-500 mb-1.5 uppercase tracking-wide">' + field.label + '</div>';
        if (isSpecial) {
            html += '<div class="text-sm font-semibold text-slate-900 break-words text-lg"><span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-gradient-to-r from-yellow-400 to-orange-500 text-white"><svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>' + value + '</span></div>';
        } else {
            html += '<div class="text-sm font-semibold text-slate-900 break-words">' + value + '</div>';
        }
        html += '</div></div></div>';
    });
    
    html += '</div>';
    
    // 描述信息
    if (header['描述']) {
        html += '<div class="mt-6 pt-6 border-t border-slate-200 bg-gradient-to-r from-slate-50 to-blue-50 rounded-lg p-5">';
        html += '<div class="flex items-center gap-2 mb-3"><svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg><span class="text-sm font-semibold text-slate-700">剧集描述</span></div>';
        html += '<p class="text-sm text-slate-700 leading-relaxed pl-6">' + header['描述'] + '</p>';
        html += '</div>';
    }
    
    html += '</div>';
    
    // 子集信息卡片
    if (episodes && episodes.length > 0) {
        html += '<div class="bg-gradient-to-br from-white to-indigo-50 border border-slate-200 rounded-xl p-6 shadow-lg">';
        html += '<div class="flex items-center gap-3 mb-6 pb-4 border-b border-slate-200">';
        html += '<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center text-white font-bold text-xl shadow-lg">';
        html += episodes.length;
        html += '</div>';
        html += '<div>';
        html += '<h3 class="text-xl font-bold text-slate-900 flex items-center gap-2">';
        html += '<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-indigo-600">';
        html += '<line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>';
        html += '</svg>子集信息</h3>';
        html += '<p class="text-sm text-slate-500 mt-1">共 ' + episodes.length + ' 集，查看详细信息</p>';
        html += '</div>';
        html += '</div>';
        html += '<div class="overflow-x-auto">';
        html += '<table class="w-full text-left border-collapse">';
        html += '<thead>';
        html += '<tr class="bg-gradient-to-r from-blue-50 to-cyan-50 border-b border-slate-200">';
        html += '<th class="px-4 py-3 text-slate-800 font-bold text-sm">子集ID</th>';
        html += '<th class="px-4 py-3 text-slate-800 font-bold text-sm">节目名称</th>';
        html += '<th class="px-4 py-3 text-slate-800 font-bold text-sm">集数</th>';
        html += '<th class="px-4 py-3 text-slate-800 font-bold text-sm">媒体拉取地址</th>';
        html += '<th class="px-4 py-3 text-slate-800 font-bold text-sm">媒体类型</th>';
        html += '<th class="px-4 py-3 text-slate-800 font-bold text-sm">编码格式</th>';
        html += '<th class="px-4 py-3 text-slate-800 font-bold text-sm">时长</th>';
        html += '<th class="px-4 py-3 text-slate-800 font-bold text-sm">文件大小</th>';
        html += '</tr>';
        html += '</thead>';
        html += '<tbody class="divide-y divide-slate-100">';
        
        episodes.forEach((episode, index) => {
            const rowBg = index % 2 === 0 ? 'bg-white' : 'bg-slate-50/30';
            html += `<tr class="${rowBg} hover:bg-blue-50/50 transition-all duration-200 border-b border-slate-100 group">`;
            html += `<td class="px-4 py-3">
                <div class="flex items-center gap-2">
                    <div class="w-9 h-9 rounded-lg bg-gradient-to-br from-slate-600 to-slate-700 flex items-center justify-center text-white font-bold text-sm shadow-md">
                        ${episode['子集id']}
                    </div>
                </div>
            </td>`;
            html += `<td class="px-4 py-3">
                <div class="font-semibold text-slate-900 text-base">${episode['节目名称']}</div>
            </td>`;
            html += `<td class="px-4 py-3">
                <span class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gradient-to-r from-blue-100 to-cyan-100 text-blue-700 text-sm font-semibold border border-blue-200">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/>
                    </svg>
                    第${episode['集数']}集
                </span>
            </td>`;
            html += `<td class="px-4 py-3 max-w-xs">
                <div class="flex items-center gap-2">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-slate-400 flex-shrink-0">
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                    </svg>
                    <span class="truncate font-mono text-xs text-slate-600" title="${episode['媒体拉取地址'] || ''}">${episode['媒体拉取地址'] || '-'}</span>
                </div>
            </td>`;
            html += `<td class="px-4 py-3">
                <span class="px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-sm font-medium">${episode['媒体类型'] || '-'}</span>
            </td>`;
            html += `<td class="px-4 py-3">
                <span class="px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-sm font-medium">${episode['编码格式'] || '-'}</span>
            </td>`;
            html += `<td class="px-4 py-3">
                <span class="inline-flex items-center gap-1.5 text-slate-700 font-medium text-sm">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-slate-500">
                        <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
                    </svg>
                    ${episode['时长'] || '-'}
                </span>
            </td>`;
            html += `<td class="px-4 py-3">
                <span class="inline-flex items-center gap-1.5 text-slate-700 font-medium text-sm">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-slate-500">
                        <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/><polyline points="3.27 6.96 12 12.01 20.73 6.96"/><line x1="12" x2="12" y1="22.08" y2="12"/>
                    </svg>
                    ${episode['文件大小'] || '-'}
                </span>
            </td>`;
            html += '</tr>';
        });
        
        html += '</tbody>';
        html += '</table>';
        html += '</div>';
        html += '</div>';
    }
    
    html += '</div>';
    
    detailBody.innerHTML = html;
}

// 返回剧集列表
function backToDramaList() {
    // 隐藏详情页面，显示列表页面
    document.getElementById('detail-page').classList.remove('active');
    document.getElementById('drama-list-page').classList.add('active');
    
    // 更新header标题
    const headerTitle = document.getElementById('header-title');
    if (headerTitle) {
        headerTitle.textContent = '剧集管理中心';
    }
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

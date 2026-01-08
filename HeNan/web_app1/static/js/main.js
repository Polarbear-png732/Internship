// API基础URL
const API_BASE = '/api';

// 当前页码
let currentPage = 1;
let pageSize = 10;
let totalPages = 1;
let currentDramaName = '';
let currentDramaId = null;
let currentCustomerId = null;
let currentCustomerName = '';
let currentDramaData = null;
let previousPageId = null; // 记录进入详情页之前的页面ID

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
        } else if (pageId === 'drama-header-management') {
            headerTitle.textContent = currentCustomerName ? `${currentCustomerName} - 剧头管理` : '剧头管理中心';
        } else if (pageId === 'copyright-management') {
            headerTitle.textContent = '版权方数据管理';
        } else if (pageId === 'placeholder') {
            headerTitle.textContent = '等待增加的模块';
        }
    }
    
    // 如果是用户列表页面，加载数据
    if (pageId === 'customer-list') {
        loadCustomerList();
    }
    
    // 如果是剧头管理页面（从导航栏点击），清除用户筛选并加载所有剧头
    if (pageId === 'drama-header-management') {
        loadAllDramaHeaders(1);
    }
    
    // 如果是版权方数据页面，加载列表
    if (pageId === 'copyright-management') {
        loadCopyrightList(1);
    }
}

// 从导航栏点击剧头管理（显示所有剧头）
function showDramaHeaderManagement() {
    currentCustomerId = null;
    currentCustomerName = '';
    showPage('drama-header-management');
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
                        class="text-blue-600 hover:text-blue-700 font-semibold text-sm inline-flex items-center gap-1.5 bg-blue-50 hover:bg-blue-100 border border-blue-200 hover:border-blue-300 px-4 py-2 rounded-lg transition-all shadow-sm hover:shadow-md group-hover:scale-105">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="16" x2="8" y1="13" y2="13"/>
                            <line x1="16" x2="8" y1="17" y2="17"/>
                            <polyline points="10 9 9 9 8 9"/>
                        </svg>
                        剧头管理
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
    
    // 切换到剧头管理页面
    showPage('drama-header-management');
    
    // 更新标题显示用户名
    const headerTitle = document.getElementById('header-title');
    if (headerTitle) {
        headerTitle.textContent = `${customerName} - 剧头管理`;
    }
    
    // 清空搜索框
    const searchInput = document.getElementById('header-search-input');
    if (searchInput) {
        searchInput.value = '';
    }
    
    // 加载该用户的剧头列表
    loadAllDramaHeaders(1);
}

// 返回用户列表
function backToCustomerList() {
    currentCustomerId = null;
    currentCustomerName = '';
    
    // 清空搜索框
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.value = '';
    }
    
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
async function searchDramas() {
    const keyword = document.getElementById('search-input')?.value?.trim() || '';
    
    if (!keyword) {
        showError('请输入要搜索的剧集名称');
        return;
    }
    
    try {
        // 使用精确搜索API直接获取剧集详情
        const response = await fetch(`${API_BASE}/dramas/search/${encodeURIComponent(keyword)}`);
        const result = await response.json();
        
        if (result.code === 200 && result.data) {
            // 直接显示详情页面
            const header = result.data.header;
            const episodes = result.data.episodes || [];
            
            currentDramaName = header['剧集名称'];
            currentDramaId = header['剧头id'];
            currentDramaData = header;
            showDramaDetailPage(header, episodes);
        } else {
            showError(result.message || '未找到该剧集');
        }
    } catch (error) {
        showError('搜索失败：' + error.message);
    }
}

// 查看剧集详情
async function viewDramaDetail(dramaId, dramaName) {
    currentDramaName = dramaName;
    currentDramaId = dramaId;
    
    // 记录来源页面
    const detailPage = document.getElementById('detail-page');
    const headerManagementPage = document.getElementById('drama-header-management-page');
    const dramaListPage = document.getElementById('drama-list-page');
    
    if (headerManagementPage && headerManagementPage.classList.contains('active')) {
        previousPageId = 'drama-header-management';
    } else if (dramaListPage && dramaListPage.classList.contains('active')) {
        previousPageId = 'drama-list';
    } else {
        previousPageId = 'customer-list';
    }
    
    try {
        // 获取剧集详情
        const response = await fetch(`${API_BASE}/dramas/${dramaId}`);
        const result = await response.json();
        
        if (result.code === 200) {
            const header = result.data;
            currentDramaData = header;
            
            // 获取子集列表
            const episodesResponse = await fetch(`${API_BASE}/dramas/${dramaId}/episodes`);
            const episodesResult = await episodesResponse.json();
            const episodes = episodesResult.code === 200 ? episodesResult.data : [];
            
            // 显示详情页面
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
    // 隐藏所有页面
    document.getElementById('drama-list-page')?.classList.remove('active');
    document.getElementById('drama-header-management-page')?.classList.remove('active');
    document.getElementById('customer-list-page')?.classList.remove('active');
    
    // 显示详情页面
    document.getElementById('detail-page').classList.add('active');
    
    // 更新标题
    const detailTitle = document.getElementById('detail-title');
    detailTitle.textContent = header['剧集名称'] || '剧集详情';
    
    // 更新header标题
    const headerTitle = document.getElementById('header-title');
    if (headerTitle) {
        headerTitle.textContent = `剧集详情 - ${header['剧集名称'] || '剧集详情'}`;
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
    // 隐藏详情页面
    document.getElementById('detail-page').classList.remove('active');
    
    // 根据记录的来源页面返回
    if (previousPageId === 'drama-header-management') {
        document.getElementById('drama-header-management-page').classList.add('active');
    } else if (previousPageId === 'drama-list') {
        document.getElementById('drama-list-page').classList.add('active');
    } else {
        // 默认返回用户列表
        document.getElementById('customer-list-page').classList.add('active');
    }
    
    // 清空来源页面记录
    previousPageId = null;
    
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

// 打开编辑模态框
function openEditModal() {
    if (!currentDramaData) {
        showError('无法获取剧集数据');
        return;
    }
    
    // 填充表单数据
    document.getElementById('edit-drama-name').value = currentDramaData['剧集名称'] || '';
    document.getElementById('edit-author-list').value = currentDramaData['作者列表'] || '';
    document.getElementById('edit-resolution').value = currentDramaData['清晰度'] || '';
    document.getElementById('edit-language').value = currentDramaData['语言'] || '';
    document.getElementById('edit-actors').value = currentDramaData['主演'] || '';
    document.getElementById('edit-content-type').value = currentDramaData['内容类型'] || '';
    document.getElementById('edit-release-year').value = currentDramaData['上映年份'] || '';
    document.getElementById('edit-keywords').value = currentDramaData['关键字'] || '';
    document.getElementById('edit-rating').value = currentDramaData['评分'] || '';
    document.getElementById('edit-recommendation').value = currentDramaData['推荐语'] || '';
    document.getElementById('edit-total-episodes').value = currentDramaData['总集数'] || '';
    document.getElementById('edit-product-category').value = currentDramaData['产品分类'] || '';
    document.getElementById('edit-vertical-image').value = currentDramaData['竖图'] || '';
    document.getElementById('edit-description').value = currentDramaData['描述'] || '';
    document.getElementById('edit-horizontal-image').value = currentDramaData['横图'] || '';
    document.getElementById('edit-copyright').value = currentDramaData['版权'] || '';
    document.getElementById('edit-secondary-category').value = currentDramaData['二级分类'] || '';
    
    // 显示模态框
    document.getElementById('edit-modal').classList.remove('hidden');
}

// 关闭编辑模态框
function closeEditModal() {
    document.getElementById('edit-modal').classList.add('hidden');
}

// 保存编辑
async function saveDramaEdit() {
    if (!currentDramaId) {
        showError('无法获取剧集ID');
        return;
    }
    
    // 验证必填字段
    const dramaName = document.getElementById('edit-drama-name').value.trim();
    if (!dramaName) {
        showError('剧集名称不能为空');
        return;
    }
    
    // 收集表单数据
    const formData = {
        '剧集名称': dramaName,
        '作者列表': document.getElementById('edit-author-list').value.trim() || '',
        '清晰度': document.getElementById('edit-resolution').value ? parseInt(document.getElementById('edit-resolution').value) : 0,
        '语言': document.getElementById('edit-language').value.trim() || '',
        '主演': document.getElementById('edit-actors').value.trim() || '',
        '内容类型': document.getElementById('edit-content-type').value.trim() || '',
        '上映年份': document.getElementById('edit-release-year').value ? parseInt(document.getElementById('edit-release-year').value) : 0,
        '关键字': document.getElementById('edit-keywords').value.trim() || '',
        '评分': document.getElementById('edit-rating').value ? parseFloat(document.getElementById('edit-rating').value) : 0.0,
        '推荐语': document.getElementById('edit-recommendation').value.trim() || '',
        '总集数': document.getElementById('edit-total-episodes').value ? parseInt(document.getElementById('edit-total-episodes').value) : 0,
        '产品分类': document.getElementById('edit-product-category').value ? parseInt(document.getElementById('edit-product-category').value) : 0,
        '竖图': document.getElementById('edit-vertical-image').value.trim() || '',
        '描述': document.getElementById('edit-description').value.trim() || '',
        '横图': document.getElementById('edit-horizontal-image').value.trim() || '',
        '版权': document.getElementById('edit-copyright').value ? parseInt(document.getElementById('edit-copyright').value) : 0,
        '二级分类': document.getElementById('edit-secondary-category').value.trim() || ''
    };
    
    try {
        const response = await fetch(`${API_BASE}/dramas/${currentDramaId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess('剧集信息更新成功！');
            closeEditModal();
            
            // 检查当前在哪个页面
            const detailPage = document.getElementById('detail-page');
            const headerManagementPage = document.getElementById('drama-header-management-page');
            
            if (detailPage && detailPage.classList.contains('active')) {
                // 在详情页，重新加载详情
                await viewDramaDetail(currentDramaId, formData['剧集名称']);
            } else if (headerManagementPage && headerManagementPage.classList.contains('active')) {
                // 在剧头管理页面，重新加载列表
                await loadAllDramaHeaders(currentPage);
            }
        } else {
            showError('更新失败：' + (result.message || '未知错误'));
        }
    } catch (error) {
        showError('更新失败：' + error.message);
    }
}

// 加载所有剧头列表
async function loadAllDramaHeaders(page = 1) {
    currentPage = page;
    
    try {
        let url = `${API_BASE}/dramas?page=${page}&page_size=${pageSize}`;
        
        // 如果有当前用户ID，按用户筛选
        if (currentCustomerId) {
            url += `&customer_id=${currentCustomerId}`;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.code === 200) {
            const dramas = result.data.list || [];
            renderDramaHeaderTable(dramas);
            renderDramaHeaderPagination(result.data);
        } else {
            showError('加载失败：' + result.message);
        }
    } catch (error) {
        showError('加载失败：' + error.message);
    }
}

// 搜索剧头
async function searchDramaHeaders(page = 1) {
    const keyword = document.getElementById('header-search-input')?.value?.trim() || '';
    
    if (!keyword) {
        // 如果没有关键词，加载所有剧头列表
        await loadAllDramaHeaders(1);
        return;
    }
    
    try {
        // 使用搜索API直接获取匹配的剧集
        const response = await fetch(`${API_BASE}/dramas/search/${encodeURIComponent(keyword)}`);
        const result = await response.json();
        
        if (result.code === 200 && result.data) {
            const header = result.data.header;
            const episodes = result.data.episodes || [];
            
            // 设置当前剧集信息
            currentDramaId = header['剧头id'];
            currentDramaName = header['剧集名称'];
            currentDramaData = header;
            
            // 记录来源页面
            previousPageId = 'drama-header-management';
            
            // 直接显示剧集详情页面
            showDramaDetailPage(header, episodes);
        } else {
            showError('未找到匹配的剧集');
        }
    } catch (error) {
        showError('搜索失败：' + error.message);
    }
}

// 渲染剧头表格
function renderDramaHeaderTable(dramas) {
    const tbody = document.getElementById('drama-header-table-body');
    
    if (!dramas || dramas.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="px-6 py-12 text-center text-slate-500"><div class="flex flex-col items-center gap-3"><svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-slate-300"><rect width="18" height="18" x="3" y="3" rx="2" ry="2"/><path d="M7 3v18"/><path d="M3 7.5h4"/><path d="M3 12h18"/><path d="M3 16.5h4"/><path d="M17 3v18"/><path d="M17 7.5h4"/><path d="M17 16.5h4"/></svg><span class="text-base">暂无剧集数据</span></div></td></tr>';
        return;
    }
    
    tbody.innerHTML = dramas.map((drama, index) => {
        const props = drama.dynamic_properties || {};
        const contentType = props['内容类型'] || '-';
        const rating = props['评分'] || 0;
        const totalEpisodes = props['总集数'] || 0;
        const authorList = props['作者列表'] || '-';
        
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
                </td>
                <td class="px-6 py-4 hidden md:table-cell">
                    <span class="text-slate-600 text-sm">${authorList}</span>
                </td>
                <td class="px-6 py-4 hidden lg:table-cell">
                    <span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 text-sm font-medium">
                        ${contentType}
                    </span>
                </td>
                <td class="px-6 py-4 hidden lg:table-cell">
                    <span class="inline-flex items-center gap-1.5 text-slate-700 font-medium text-sm">
                        ${totalEpisodes} 集
                    </span>
                </td>
                <td class="px-6 py-4 hidden lg:table-cell">
                    ${rating ? `<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-gradient-to-r from-orange-100 to-amber-100 text-orange-700 font-semibold text-sm border border-orange-200">
                        ${rating}
                    </span>` : '<span class="text-slate-400">-</span>'}
                </td>
                <td class="px-6 py-4 text-right">
                    <div class="flex items-center justify-end gap-2">
                        <button onclick="editDramaHeader(${drama.drama_id}, '${drama.drama_name.replace(/'/g, "\\'")}')" 
                            class="text-blue-600 hover:text-blue-700 font-medium text-sm inline-flex items-center gap-1.5 bg-blue-50 hover:bg-blue-100 border border-blue-200 hover:border-blue-300 px-3 py-1.5 rounded-lg transition-all shadow-sm hover:shadow-md">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                            </svg>
                            编辑
                        </button>
                        <button onclick="deleteDramaHeader(${drama.drama_id}, '${drama.drama_name.replace(/'/g, "\\'")}')" 
                            class="text-red-600 hover:text-red-700 font-medium text-sm inline-flex items-center gap-1.5 bg-red-50 hover:bg-red-100 border border-red-200 hover:border-red-300 px-3 py-1.5 rounded-lg transition-all shadow-sm hover:shadow-md">
                            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <polyline points="3 6 5 6 21 6"/>
                                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                            </svg>
                            删除
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// 渲染剧头分页
function renderDramaHeaderPagination(data) {
    totalPages = data.total_pages;
    const pagination = document.getElementById('header-pagination');
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    // 检查是否有搜索关键词
    const keyword = document.getElementById('header-search-input')?.value?.trim() || '';
    const paginationFunction = keyword ? 'searchDramaHeaders' : 'loadAllDramaHeaders';
    
    pagination.innerHTML = `
        <button ${currentPage === 1 ? 'disabled' : ''} 
            onclick="${paginationFunction}(${currentPage - 1})"
            class="px-4 py-2 border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            上一页
        </button>
        <span class="text-sm text-slate-600 mx-4">第 ${currentPage} / ${totalPages} 页，共 ${data.total} 条</span>
        <button ${currentPage === totalPages ? 'disabled' : ''} 
            onclick="${paginationFunction}(${currentPage + 1})"
            class="px-4 py-2 border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            下一页
        </button>
    `;
}

// 切换全选
function toggleSelectAllHeaders(checked) {
    const checkboxes = document.querySelectorAll('.header-checkbox');
    checkboxes.forEach(cb => {
        cb.checked = checked;
    });
}

// 更新全选复选框状态
function updateSelectAllCheckbox() {
    const checkboxes = document.querySelectorAll('.header-checkbox');
    const selectAll = document.getElementById('select-all-headers');
    if (checkboxes.length === 0) {
        if (selectAll) selectAll.checked = false;
        return;
    }
    const allChecked = Array.from(checkboxes).every(cb => cb.checked);
    if (selectAll) selectAll.checked = allChecked;
}

// 打开添加剧头模态框
function openAddDramaHeaderModal() {
    // 清空表单
    document.getElementById('add-drama-name').value = '';
    document.getElementById('add-customer-id').value = '';
    document.getElementById('add-author-list').value = '';
    document.getElementById('add-resolution').value = '';
    document.getElementById('add-language').value = '';
    document.getElementById('add-actors').value = '';
    document.getElementById('add-content-type').value = '';
    document.getElementById('add-release-year').value = '';
    document.getElementById('add-keywords').value = '';
    document.getElementById('add-rating').value = '';
    document.getElementById('add-recommendation').value = '';
    document.getElementById('add-total-episodes').value = '';
    document.getElementById('add-product-category').value = '';
    document.getElementById('add-vertical-image').value = '';
    document.getElementById('add-description').value = '';
    document.getElementById('add-horizontal-image').value = '';
    document.getElementById('add-copyright').value = '';
    document.getElementById('add-secondary-category').value = '';
    
    // 显示模态框
    document.getElementById('add-header-modal').classList.remove('hidden');
}

// 关闭添加剧头模态框
function closeAddDramaHeaderModal() {
    document.getElementById('add-header-modal').classList.add('hidden');
}

// 保存添加的剧头
async function saveAddDramaHeader() {
    const dramaName = document.getElementById('add-drama-name').value.trim();
    if (!dramaName) {
        showError('剧集名称不能为空');
        return;
    }
    
    // 收集表单数据
    const formData = {
        '剧集名称': dramaName,
        'customer_id': document.getElementById('add-customer-id').value ? parseInt(document.getElementById('add-customer-id').value) : null,
        '作者列表': document.getElementById('add-author-list').value.trim() || '',
        '清晰度': document.getElementById('add-resolution').value ? parseInt(document.getElementById('add-resolution').value) : 0,
        '语言': document.getElementById('add-language').value.trim() || '',
        '主演': document.getElementById('add-actors').value.trim() || '',
        '内容类型': document.getElementById('add-content-type').value.trim() || '',
        '上映年份': document.getElementById('add-release-year').value ? parseInt(document.getElementById('add-release-year').value) : 0,
        '关键字': document.getElementById('add-keywords').value.trim() || '',
        '评分': document.getElementById('add-rating').value ? parseFloat(document.getElementById('add-rating').value) : 0.0,
        '推荐语': document.getElementById('add-recommendation').value.trim() || '',
        '总集数': document.getElementById('add-total-episodes').value ? parseInt(document.getElementById('add-total-episodes').value) : 0,
        '产品分类': document.getElementById('add-product-category').value ? parseInt(document.getElementById('add-product-category').value) : 0,
        '竖图': document.getElementById('add-vertical-image').value.trim() || '',
        '描述': document.getElementById('add-description').value.trim() || '',
        '横图': document.getElementById('add-horizontal-image').value.trim() || '',
        '版权': document.getElementById('add-copyright').value ? parseInt(document.getElementById('add-copyright').value) : 0,
        '二级分类': document.getElementById('add-secondary-category').value.trim() || ''
    };
    
    try {
        const response = await fetch(`${API_BASE}/dramas`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess('剧头添加成功！');
            closeAddDramaHeaderModal();
            // 重新加载列表
            await loadAllDramaHeaders(currentPage);
        } else {
            showError('添加失败：' + (result.message || '未知错误'));
        }
    } catch (error) {
        showError('添加失败：' + error.message);
    }
}

// 编辑剧头
async function editDramaHeader(dramaId, dramaName) {
    currentDramaId = dramaId;
    
    try {
        // 获取剧集详情
        const response = await fetch(`${API_BASE}/dramas/${dramaId}`);
        const result = await response.json();
        
        if (result.code === 200) {
            const header = result.data;
            currentDramaData = header;
            
            // 填充表单数据
            document.getElementById('edit-drama-name').value = header['剧集名称'] || '';
            document.getElementById('edit-author-list').value = header['作者列表'] || '';
            document.getElementById('edit-resolution').value = header['清晰度'] || '';
            document.getElementById('edit-language').value = header['语言'] || '';
            document.getElementById('edit-actors').value = header['主演'] || '';
            document.getElementById('edit-content-type').value = header['内容类型'] || '';
            document.getElementById('edit-release-year').value = header['上映年份'] || '';
            document.getElementById('edit-keywords').value = header['关键字'] || '';
            document.getElementById('edit-rating').value = header['评分'] || '';
            document.getElementById('edit-recommendation').value = header['推荐语'] || '';
            document.getElementById('edit-total-episodes').value = header['总集数'] || '';
            document.getElementById('edit-product-category').value = header['产品分类'] || '';
            document.getElementById('edit-vertical-image').value = header['竖图'] || '';
            document.getElementById('edit-description').value = header['描述'] || '';
            document.getElementById('edit-horizontal-image').value = header['横图'] || '';
            document.getElementById('edit-copyright').value = header['版权'] || '';
            document.getElementById('edit-secondary-category').value = header['二级分类'] || '';
            
            // 显示编辑模态框
            document.getElementById('edit-modal').classList.remove('hidden');
        } else {
            showError('获取详情失败：' + result.message);
        }
    } catch (error) {
        showError('获取详情失败：' + error.message);
    }
}

// 删除剧头
async function deleteDramaHeader(dramaId, dramaName) {
    if (!confirm(`确定要删除剧集"${dramaName}"吗？此操作不可撤销！`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/dramas/${dramaId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess('剧头删除成功！');
            // 重新加载列表
            await loadAllDramaHeaders(currentPage);
        } else {
            showError('删除失败：' + (result.message || '未知错误'));
        }
    } catch (error) {
        showError('删除失败：' + error.message);
    }
}

// 批量删除剧头
async function batchDeleteDramaHeaders() {
    const checkboxes = document.querySelectorAll('.header-checkbox:checked');
    const selectedIds = Array.from(checkboxes).map(cb => parseInt(cb.value));
    
    if (selectedIds.length === 0) {
        showError('请至少选择一个剧集');
        return;
    }
    
    if (!confirm(`确定要删除选中的 ${selectedIds.length} 个剧集吗？此操作不可撤销！`)) {
        return;
    }
    
    try {
        // 逐个删除
        let successCount = 0;
        let failCount = 0;
        
        for (const dramaId of selectedIds) {
            try {
                const response = await fetch(`${API_BASE}/dramas/${dramaId}`, {
                    method: 'DELETE'
                });
                const result = await response.json();
                if (result.code === 200) {
                    successCount++;
                } else {
                    failCount++;
                }
            } catch (error) {
                failCount++;
            }
        }
        
        if (failCount === 0) {
            showSuccess(`成功删除 ${successCount} 个剧集！`);
        } else {
            showError(`成功删除 ${successCount} 个，失败 ${failCount} 个`);
        }
        
        // 重新加载列表
        await loadAllDramaHeaders(currentPage);
    } catch (error) {
        showError('批量删除失败：' + error.message);
    }
}


// ==================== 版权方数据管理 ====================

let copyrightCurrentPage = 1;

// 加载版权方数据列表
async function loadCopyrightList(page = 1) {
    copyrightCurrentPage = page;
    const keyword = document.getElementById('copyright-search-input')?.value?.trim() || '';
    
    try {
        let url = `${API_BASE}/copyright?page=${page}&page_size=${pageSize}`;
        if (keyword) {
            url += `&keyword=${encodeURIComponent(keyword)}`;
        }
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (result.code === 200) {
            renderCopyrightTable(result.data.list);
            renderCopyrightPagination(result.data);
        } else {
            showError('加载数据失败：' + result.message);
        }
    } catch (error) {
        showError('加载数据失败：' + error.message);
    }
}

// 搜索版权方数据
function searchCopyrightContent() {
    loadCopyrightList(1);
}

// 渲染版权方数据表格
function renderCopyrightTable(items) {
    const tbody = document.getElementById('copyright-table-body');
    
    if (!items || items.length === 0) {
        tbody.innerHTML = '<tr><td colspan="30" class="px-6 py-12 text-center text-slate-500"><div class="flex flex-col items-center gap-3"><svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="text-slate-300"><path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"/></svg><span class="text-base">暂无版权方数据</span></div></td></tr>';
        return;
    }
    
    tbody.innerHTML = items.map((item, index) => {
        const rowClass = index % 2 === 0 ? 'bg-white' : 'bg-slate-50/30';
        const truncate = (text, len = 20) => {
            if (!text) return '-';
            return text.length > len ? text.substring(0, len) + '...' : text;
        };
        return `
            <tr class="${rowClass} hover:bg-blue-50/50 transition-all duration-200 border-b border-slate-100 group">
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.serial_number || item.id || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.upstream_copyright, 15)}</td>
                <td class="px-4 py-3 text-sm font-medium text-slate-900 whitespace-nowrap">${truncate(item.media_name, 20)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.category_level1 || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.category_level1_henan || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.category_level2_henan || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.episode_count || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.single_episode_duration || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.total_duration || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.production_year || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.authorization_region, 10)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.authorization_platform, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.cooperation_mode, 10)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.production_region, 10)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.language || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.language_henan || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.country || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.director, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.screenwriter, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.cast_members, 20)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.recommendation, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.synopsis, 20)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.keywords, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.video_quality || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${truncate(item.license_number, 15)}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.rating || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.exclusive_status || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.copyright_start_date || '-'}</td>
                <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${item.copyright_end_date || '-'}</td>
                <td class="px-4 py-3 text-right whitespace-nowrap sticky right-0 ${rowClass} group-hover:bg-blue-50/50">
                    <div class="flex items-center justify-end gap-2">
                        <button onclick="editCopyrightContent(${item.id})" 
                            class="text-blue-600 hover:text-blue-700 font-medium text-sm inline-flex items-center gap-1 bg-blue-50 hover:bg-blue-100 border border-blue-200 px-2 py-1 rounded-lg transition-all">
                            编辑
                        </button>
                        <button onclick="deleteCopyrightContent(${item.id}, '${(item.media_name || '').replace(/'/g, "\\'")}')" 
                            class="text-red-600 hover:text-red-700 font-medium text-sm inline-flex items-center gap-1 bg-red-50 hover:bg-red-100 border border-red-200 px-2 py-1 rounded-lg transition-all">
                            删除
                        </button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

// 渲染版权方数据分页
function renderCopyrightPagination(data) {
    const pagination = document.getElementById('copyright-pagination');
    const totalPages = data.total_pages;
    
    if (totalPages <= 1) {
        pagination.innerHTML = '';
        return;
    }
    
    pagination.innerHTML = `
        <button ${copyrightCurrentPage === 1 ? 'disabled' : ''} 
            onclick="loadCopyrightList(${copyrightCurrentPage - 1})"
            class="px-4 py-2 border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            上一页
        </button>
        <span class="text-sm text-slate-600 mx-4">第 ${copyrightCurrentPage} / ${totalPages} 页，共 ${data.total} 条</span>
        <button ${copyrightCurrentPage === totalPages ? 'disabled' : ''} 
            onclick="loadCopyrightList(${copyrightCurrentPage + 1})"
            class="px-4 py-2 border border-slate-300 rounded-lg bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors">
            下一页
        </button>
    `;
}

// 打开添加版权方数据模态框
function openAddCopyrightModal() {
    document.getElementById('copyright-modal-title').innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600">
            <line x1="12" x2="12" y1="5" y2="19"/>
            <line x1="5" x2="19" y1="12" y2="12"/>
        </svg>
        添加版权方数据
    `;
    document.getElementById('copyright-edit-id').value = '';
    document.getElementById('add-copyright-form').reset();
    document.getElementById('add-copyright-modal').classList.remove('hidden');
}

// 关闭添加版权方数据模态框
function closeAddCopyrightModal() {
    document.getElementById('add-copyright-modal').classList.add('hidden');
}

// 编辑版权方数据
async function editCopyrightContent(id) {
    try {
        const response = await fetch(`${API_BASE}/copyright/${id}`);
        const result = await response.json();
        
        if (result.code === 200) {
            const item = result.data;
            
            document.getElementById('copyright-modal-title').innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="text-blue-600">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
                编辑版权方数据
            `;
            
            document.getElementById('copyright-edit-id').value = id;
            document.getElementById('copyright-media-name').value = item.media_name || '';
            document.getElementById('copyright-upstream').value = item.upstream_copyright || '';
            document.getElementById('copyright-category1').value = item.category_level1 || '';
            document.getElementById('copyright-category1-henan').value = item.category_level1_henan || '';
            document.getElementById('copyright-category2-henan').value = item.category_level2_henan || '';
            document.getElementById('copyright-episode-count').value = item.episode_count || '';
            document.getElementById('copyright-single-duration').value = item.single_episode_duration || '';
            document.getElementById('copyright-total-duration').value = item.total_duration || '';
            document.getElementById('copyright-production-year').value = item.production_year || '';
            document.getElementById('copyright-production-region').value = item.production_region || '';
            document.getElementById('copyright-language').value = item.language || '';
            document.getElementById('copyright-country').value = item.country || '';
            document.getElementById('copyright-director').value = item.director || '';
            document.getElementById('copyright-screenwriter').value = item.screenwriter || '';
            document.getElementById('copyright-rating').value = item.rating || '';
            document.getElementById('copyright-exclusive').value = item.exclusive_status || '';
            document.getElementById('copyright-cast').value = item.cast_members || '';
            document.getElementById('copyright-synopsis').value = item.synopsis || '';
            
            document.getElementById('add-copyright-modal').classList.remove('hidden');
        } else {
            showError('获取数据失败：' + result.message);
        }
    } catch (error) {
        showError('获取数据失败：' + error.message);
    }
}

// 保存版权方数据
async function saveCopyrightContent() {
    const editId = document.getElementById('copyright-edit-id').value;
    const mediaName = document.getElementById('copyright-media-name').value.trim();
    
    if (!mediaName) {
        showError('介质名称不能为空');
        return;
    }
    
    const data = {
        media_name: mediaName,
        upstream_copyright: document.getElementById('copyright-upstream').value.trim() || null,
        category_level1: document.getElementById('copyright-category1').value.trim() || null,
        category_level1_henan: document.getElementById('copyright-category1-henan').value.trim() || null,
        category_level2_henan: document.getElementById('copyright-category2-henan').value.trim() || null,
        episode_count: parseInt(document.getElementById('copyright-episode-count').value) || null,
        single_episode_duration: parseFloat(document.getElementById('copyright-single-duration').value) || null,
        total_duration: parseFloat(document.getElementById('copyright-total-duration').value) || null,
        production_year: parseInt(document.getElementById('copyright-production-year').value) || null,
        production_region: document.getElementById('copyright-production-region').value.trim() || null,
        language: document.getElementById('copyright-language').value.trim() || null,
        country: document.getElementById('copyright-country').value.trim() || null,
        director: document.getElementById('copyright-director').value.trim() || null,
        screenwriter: document.getElementById('copyright-screenwriter').value.trim() || null,
        rating: parseFloat(document.getElementById('copyright-rating').value) || null,
        exclusive_status: document.getElementById('copyright-exclusive').value.trim() || null,
        cast_members: document.getElementById('copyright-cast').value.trim() || null,
        synopsis: document.getElementById('copyright-synopsis').value.trim() || null
    };
    
    try {
        let url = `${API_BASE}/copyright`;
        let method = 'POST';
        
        if (editId) {
            url = `${API_BASE}/copyright/${editId}`;
            method = 'PUT';
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess(editId ? '更新成功！' : '添加成功！');
            closeAddCopyrightModal();
            loadCopyrightList(copyrightCurrentPage);
        } else {
            showError(result.message || '保存失败');
        }
    } catch (error) {
        showError('保存失败：' + error.message);
    }
}

// 删除版权方数据
async function deleteCopyrightContent(id, mediaName) {
    if (!confirm(`确定要删除"${mediaName}"吗？此操作不可撤销！`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/copyright/${id}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess('删除成功！');
            loadCopyrightList(copyrightCurrentPage);
        } else {
            showError(result.message || '删除失败');
        }
    } catch (error) {
        showError('删除失败：' + error.message);
    }
}

// API基础URL
const API_BASE = '/api';

// 全局状态变量
let pageSize = 10;
let currentDramaName = '';
let currentDramaId = null;
let currentCustomerId = null;
let currentCustomerName = '';
let currentDramaData = null;

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
        tbody.innerHTML = '<tr><td colspan="3" class="px-6 py-8 text-center text-slate-500">暂无用户数据</td></tr>';
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
}

// 导出Excel
async function exportDrama() {
    if (!currentDramaId) {
        showError('请先选择或查询一个剧集');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/dramas/${currentDramaId}/export`);
        
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
                // 在剧头管理页面，重新搜索
                const keyword = document.getElementById('header-search-input')?.value?.trim() || '';
                if (keyword) {
                    await searchDramaHeaderDirect();
                }
            }
        } else {
            showError('更新失败：' + (result.message || '未知错误'));
        }
    } catch (error) {
        showError('更新失败：' + error.message);
    }
}

// 剧头管理页面 - 直接搜索并显示结果
async function searchDramaHeaderDirect() {
    const keyword = document.getElementById('header-search-input')?.value?.trim() || '';
    const resultContainer = document.getElementById('header-search-result');
    
    if (!keyword) {
        showError('请输入剧集名称进行搜索');
        resultContainer.classList.add('hidden');
        return;
    }
    
    try {
        // 使用搜索API获取剧集详情
        const response = await fetch(`${API_BASE}/dramas/by-name?name=${encodeURIComponent(keyword)}`);
        
        if (!response.ok) {
            const error = await response.json();
            resultContainer.innerHTML = `
                <div class="bg-white border border-slate-200 rounded-xl p-8 text-center">
                    <div class="text-slate-400 mb-2">
                        <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" class="mx-auto">
                            <circle cx="11" cy="11" r="8"/>
                            <path d="m21 21-4.3-4.3"/>
                        </svg>
                    </div>
                    <p class="text-slate-500">${error.detail || '未找到匹配的剧集'}</p>
                </div>
            `;
            resultContainer.classList.remove('hidden');
            return;
        }
        
        const result = await response.json();
        
        if (result.code === 200 && result.data) {
            const header = result.data.header;
            const episodes = result.data.episodes || [];
            
            // 设置当前剧集信息
            currentDramaId = header['剧头id'];
            currentDramaName = header['剧集名称'];
            currentDramaData = header;
            
            // 在当前页面下方显示详情
            renderDramaDetailInline(header, episodes, resultContainer);
            resultContainer.classList.remove('hidden');
        } else {
            resultContainer.innerHTML = `
                <div class="bg-white border border-slate-200 rounded-xl p-8 text-center">
                    <p class="text-slate-500">未找到匹配的剧集</p>
                </div>
            `;
            resultContainer.classList.remove('hidden');
        }
    } catch (error) {
        showError('搜索失败：' + error.message);
    }
}

// 在剧头管理页面内联显示剧集详情
function renderDramaDetailInline(header, episodes, container) {
    let html = '<div class="space-y-6">';
    
    // 剧集基本信息卡片
    html += '<div class="bg-gradient-to-br from-white to-slate-50 border border-slate-200 rounded-xl p-6 shadow-lg">';
    html += '<div class="flex items-center justify-between mb-6 pb-4 border-b border-slate-200">';
    html += '<div class="flex items-center gap-3">';
    html += '<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-xl shadow-lg">';
    html += (header['剧集名称'] ? header['剧集名称'].charAt(0) : '剧');
    html += '</div>';
    html += '<div><h3 class="text-xl font-bold text-slate-900">' + (header['剧集名称'] || '剧集详情') + '</h3>';
    html += '<p class="text-sm text-slate-500 mt-1">剧集ID: ' + (header['剧头id'] || '-') + '</p></div>';
    html += '</div>';
    html += '<div class="flex items-center gap-2">';
    html += `<button onclick="editDramaHeader(${header['剧头id']}, '${(header['剧集名称'] || '').replace(/'/g, "\\'")}')" 
        class="text-blue-600 hover:text-blue-700 font-medium text-sm inline-flex items-center gap-1.5 bg-blue-50 hover:bg-blue-100 border border-blue-200 hover:border-blue-300 px-3 py-1.5 rounded-lg transition-all">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
        </svg>
        编辑
    </button>`;
    html += `<button onclick="exportDramaById(${header['剧头id']})" 
        class="text-green-600 hover:text-green-700 font-medium text-sm inline-flex items-center gap-1.5 bg-green-50 hover:bg-green-100 border border-green-200 hover:border-green-300 px-3 py-1.5 rounded-lg transition-all">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" x2="12" y1="15" y2="3"/>
        </svg>
        导出
    </button>`;
    html += '</div></div>';
    
    // 基本信息网格
    html += '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">';
    const fields = [
        { label: '作者列表', key: '作者列表' },
        { label: '清晰度', key: '清晰度' },
        { label: '语言', key: '语言' },
        { label: '主演', key: '主演' },
        { label: '内容类型', key: '内容类型' },
        { label: '上映年份', key: '上映年份' },
        { label: '关键字', key: '关键字' },
        { label: '评分', key: '评分' },
        { label: '总集数', key: '总集数' },
        { label: '产品分类', key: '产品分类' },
        { label: '版权', key: '版权' },
        { label: '二级分类', key: '二级分类' }
    ];
    
    fields.forEach(field => {
        const value = header[field.key] !== null && header[field.key] !== undefined ? header[field.key] : '-';
        html += `<div class="bg-white border border-slate-200 rounded-lg p-3">
            <div class="text-xs font-medium text-slate-500 mb-1">${field.label}</div>
            <div class="text-sm font-semibold text-slate-900">${value}</div>
        </div>`;
    });
    html += '</div>';
    
    // 推荐语和描述
    if (header['推荐语']) {
        html += `<div class="bg-blue-50 border border-blue-200 rounded-lg p-4 mt-4">
            <div class="text-xs font-medium text-blue-600 mb-1">推荐语</div>
            <div class="text-sm text-blue-800">${header['推荐语']}</div>
        </div>`;
    }
    if (header['描述']) {
        html += `<div class="bg-slate-50 border border-slate-200 rounded-lg p-4 mt-4">
            <div class="text-xs font-medium text-slate-600 mb-1">描述</div>
            <div class="text-sm text-slate-700">${header['描述']}</div>
        </div>`;
    }
    html += '</div>';
    
    // 子集信息
    html += '<div class="bg-gradient-to-br from-white to-indigo-50 border border-slate-200 rounded-xl p-6 shadow-lg">';
    html += '<div class="flex items-center justify-between mb-4 pb-4 border-b border-slate-200">';
    html += '<h3 class="text-lg font-bold text-slate-900">子集信息 (' + episodes.length + ' 集)</h3>';
    html += `<button onclick="openAddEpisodeModal(${header['剧头id']})" 
        class="text-blue-600 hover:text-blue-700 font-medium text-sm inline-flex items-center gap-1.5 bg-blue-50 hover:bg-blue-100 border border-blue-200 hover:border-blue-300 px-3 py-1.5 rounded-lg transition-all">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <line x1="12" x2="12" y1="5" y2="19"/>
            <line x1="5" x2="19" y1="12" y2="12"/>
        </svg>
        添加子集
    </button>`;
    html += '</div>';
    
    if (episodes.length > 0) {
        html += '<div class="overflow-x-auto"><table class="w-full text-left text-sm">';
        html += '<thead><tr class="bg-slate-100 border-b border-slate-200">';
        html += '<th class="px-4 py-2 font-semibold text-slate-700">集数ID</th>';
        html += '<th class="px-4 py-2 font-semibold text-slate-700">节目名称</th>';
        html += '<th class="px-4 py-2 font-semibold text-slate-700">媒体拉取地址</th>';
        html += '<th class="px-4 py-2 font-semibold text-slate-700">时长</th>';
        html += '<th class="px-4 py-2 font-semibold text-slate-700">文件大小</th>';
        html += '<th class="px-4 py-2 font-semibold text-slate-700 text-right">操作</th>';
        html += '</tr></thead><tbody>';
        
        episodes.forEach((ep, index) => {
            // 支持两种数据格式：中文字段名（by-name API）和英文字段名（episodes API）
            const episodeId = ep['子集id'] || ep.episode_id || 0;
            const episodeName = ep['节目名称'] || ep.episode_name || '';
            const mediaUrl = ep['媒体拉取地址'] || (ep.dynamic_properties && ep.dynamic_properties['媒体拉取地址']) || '';
            const mediaType = ep['媒体类型'] || (ep.dynamic_properties && ep.dynamic_properties['媒体类型']) || 0;
            const encoding = ep['编码格式'] || (ep.dynamic_properties && ep.dynamic_properties['编码格式']) || 0;
            const episodeNum = ep['集数'] || (ep.dynamic_properties && ep.dynamic_properties['集数']) || 0;
            const duration = ep['时长'] || (ep.dynamic_properties && ep.dynamic_properties['时长']) || 0;
            const fileSize = ep['文件大小'] || (ep.dynamic_properties && ep.dynamic_properties['文件大小']) || 0;
            
            const rowClass = index % 2 === 0 ? 'bg-white' : 'bg-slate-50/50';
            html += `<tr class="${rowClass} border-b border-slate-100 hover:bg-blue-50/50">`;
            html += `<td class="px-4 py-2 text-slate-600">${episodeId}</td>`;
            html += `<td class="px-4 py-2 font-medium text-slate-900">${episodeName}</td>`;
            html += `<td class="px-4 py-2"><a href="${mediaUrl || '#'}" target="_blank" class="text-blue-600 hover:text-blue-700 hover:underline text-xs font-mono truncate max-w-xs inline-block" title="${mediaUrl || '暂无'}">${mediaUrl || '暂无'}</a></td>`;
            html += `<td class="px-4 py-2 text-slate-600">${duration || '-'}</td>`;
            html += `<td class="px-4 py-2 text-slate-600">${fileSize || '-'}</td>`;
            html += `<td class="px-4 py-2 text-right">
                <button onclick="openEditEpisodeModal(${episodeId}, '${episodeName.replace(/'/g, "\\'")}', '${String(mediaUrl).replace(/'/g, "\\'")}', ${mediaType}, ${encoding}, ${episodeNum}, '${duration}', ${fileSize})" class="text-blue-600 hover:text-blue-700 text-sm mr-2">编辑</button>
                <button onclick="deleteEpisode(${episodeId}, '${episodeName.replace(/'/g, "\\'")}')" class="text-red-600 hover:text-red-700 text-sm">删除</button>
            </td>`;
            html += '</tr>';
        });
        
        html += '</tbody></table></div>';
    } else {
        html += '<div class="text-center py-8 text-slate-500">暂无子集数据</div>';
    }
    html += '</div>';
    
    html += '</div>';
    container.innerHTML = html;
}

// 按ID导出剧集
async function exportDramaById(dramaId) {
    try {
        window.location.href = `${API_BASE}/dramas/${dramaId}/export`;
    } catch (error) {
        showError('导出失败：' + error.message);
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
            // 重新搜索刷新页面
            searchDramaHeaderDirect();
        } else {
            showError('删除失败：' + (result.message || '未知错误'));
        }
    } catch (error) {
        showError('删除失败：' + error.message);
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
async function openAddCopyrightModal() {
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
    // 清空edit-id，防止下次打开时误用
    document.getElementById('copyright-edit-id').value = '';
    document.getElementById('add-copyright-form').reset();
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
    
    console.log('saveCopyrightContent - editId:', editId, 'type:', typeof editId);
    
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
        language_henan: document.getElementById('copyright-language').value.trim() || null,  // 暂时用 language 字段
        country: document.getElementById('copyright-country').value.trim() || null,
        director: document.getElementById('copyright-director').value.trim() || null,
        screenwriter: document.getElementById('copyright-screenwriter').value.trim() || null,
        rating: parseFloat(document.getElementById('copyright-rating').value) || null,
        exclusive_status: document.getElementById('copyright-exclusive').value.trim() || null,
        cast_members: document.getElementById('copyright-cast').value.trim() || null,
        recommendation: null,  // 暂时为空
        synopsis: document.getElementById('copyright-synopsis').value.trim() || null,
        keywords: null  // 暂时为空
    };
    
    try {
        let url = `${API_BASE}/copyright`;
        let method = 'POST';
        
        // 更严格的判断：editId存在且不为空字符串
        if (editId && editId.trim() !== '') {
            url = `${API_BASE}/copyright/${editId}`;
            method = 'PUT';
            console.log('执行更新操作，URL:', url);
        } else {
            console.log('执行新增操作，URL:', url);
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
            showSuccess(editId ? '更新成功！' : '添加成功！自动创建了剧头和子集数据');
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


// ==================== 子集管理功能 ====================

let currentEditEpisodeId = null;

// 打开添加子集模态框
function openAddEpisodeModal() {
    if (!currentDramaId) {
        showError('请先选择一个剧集');
        return;
    }
    
    // 清空表单
    document.getElementById('episode-name').value = '';
    document.getElementById('episode-media-url').value = '';
    document.getElementById('episode-media-type').value = '';
    document.getElementById('episode-encoding').value = '';
    document.getElementById('episode-number').value = '';
    document.getElementById('episode-duration').value = '';
    document.getElementById('episode-file-size').value = '';
    
    currentEditEpisodeId = null;
    document.getElementById('episode-modal-title').textContent = '添加子集';
    document.getElementById('episode-modal').classList.remove('hidden');
}

// 打开编辑子集模态框
function openEditEpisodeModal(episodeId, name, mediaUrl, mediaType, encoding, episodeNum, duration, fileSize) {
    currentEditEpisodeId = episodeId;
    
    document.getElementById('episode-name').value = name || '';
    document.getElementById('episode-media-url').value = mediaUrl || '';
    document.getElementById('episode-media-type').value = mediaType || '';
    document.getElementById('episode-encoding').value = encoding || '';
    document.getElementById('episode-number').value = episodeNum || '';
    document.getElementById('episode-duration').value = duration || '';
    document.getElementById('episode-file-size').value = fileSize || '';
    
    document.getElementById('episode-modal-title').textContent = '编辑子集';
    document.getElementById('episode-modal').classList.remove('hidden');
}

// 关闭子集模态框
function closeEpisodeModal() {
    document.getElementById('episode-modal').classList.add('hidden');
    currentEditEpisodeId = null;
}

// 保存子集
async function saveEpisode() {
    const episodeName = document.getElementById('episode-name').value.trim();
    if (!episodeName) {
        showError('节目名称不能为空');
        return;
    }
    
    const formData = {
        '节目名称': episodeName,
        '媒体拉取地址': document.getElementById('episode-media-url').value.trim() || '',
        '媒体类型': parseInt(document.getElementById('episode-media-type').value) || 0,
        '编码格式': parseInt(document.getElementById('episode-encoding').value) || 0,
        '集数': parseInt(document.getElementById('episode-number').value) || 0,
        '时长': parseInt(document.getElementById('episode-duration').value) || 0,
        '文件大小': parseInt(document.getElementById('episode-file-size').value) || 0
    };
    
    try {
        let url = `${API_BASE}/dramas/${currentDramaId}/episodes`;
        let method = 'POST';
        
        if (currentEditEpisodeId) {
            url = `${API_BASE}/dramas/${currentDramaId}/episodes/${currentEditEpisodeId}`;
            method = 'PUT';
        }
        
        const response = await fetch(url, {
            method: method,
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess(currentEditEpisodeId ? '子集更新成功！' : '子集添加成功！');
            closeEpisodeModal();
            // 重新加载详情页
            await refreshDramaDetail();
        } else {
            showError('操作失败：' + (result.message || '未知错误'));
        }
    } catch (error) {
        showError('操作失败：' + error.message);
    }
}

// 删除子集
async function deleteEpisode(episodeId, episodeName) {
    if (!confirm(`确定要删除子集"${episodeName}"吗？此操作不可恢复。`)) {
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/dramas/${currentDramaId}/episodes/${episodeId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.code === 200) {
            showSuccess('子集删除成功！');
            // 重新加载详情页
            await refreshDramaDetail();
        } else {
            showError('删除失败：' + (result.message || '未知错误'));
        }
    } catch (error) {
        showError('删除失败：' + error.message);
    }
}

// 刷新剧集详情页
async function refreshDramaDetail() {
    if (!currentDramaId) return;
    
    try {
        // 获取剧集详情
        const response = await fetch(`${API_BASE}/dramas/${currentDramaId}`);
        const result = await response.json();
        
        if (result.code === 200) {
            const header = result.data;
            currentDramaData = header;
            currentDramaName = header['剧集名称'];
            
            // 获取子集列表
            const episodesResponse = await fetch(`${API_BASE}/dramas/${currentDramaId}/episodes`);
            const episodesResult = await episodesResponse.json();
            const episodes = episodesResult.code === 200 ? episodesResult.data : [];
            
            // 重新渲染详情（在剧头管理页面内联显示）
            const resultContainer = document.getElementById('header-search-result');
            if (resultContainer) {
                renderDramaDetailInline(header, episodes, resultContainer);
            }
        }
    } catch (error) {
        showError('刷新失败：' + error.message);
    }
}

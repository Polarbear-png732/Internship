/**
 * 通用模块（common）
 *
 * 职责：
 * - 全局常量与共享状态（API_BASE、当前客户/剧集上下文）
 * - 页面切换与导航高亮
 * - 客户/剧头/子集的通用交互与基础操作
 * - Toast 通知与通用 UI 工具函数
 *
 * 依赖关系：
 * - 被 copyright.js / backfill.js / scan.js 复用
 * - 需优先于其他业务脚本加载
 */

// API基础URL
const API_BASE = '/api';

// 全局状态变量
let pageSize = 10;
const SIDEBAR_COLLAPSE_KEY = 'app.sidebar.collapsed';
let currentDramaName = '';
let currentDramaId = null;
let currentCustomerId = null;
let currentCustomerCode = null;  // 客户代码（如 henan_mobile）
let currentCustomerName = '';
let currentDramaData = null;
let currentDramaColumns = [];    // 当前客户的剧头列配置
let currentEpisodeColumns = [];  // 当前客户的子集列配置

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
    initializeSidebarState();
    loadCustomerList();
});

function applySidebarState(collapsed) {
    const app = document.getElementById('app');
    if (!app) return;

    app.classList.toggle('sidebar-collapsed', collapsed);
}

function initializeSidebarState() {
    const collapsed = localStorage.getItem(SIDEBAR_COLLAPSE_KEY) === '1';
    applySidebarState(collapsed);
}

function toggleSidebar() {
    const app = document.getElementById('app');
    if (!app) return;
    const collapsed = !app.classList.contains('sidebar-collapsed');
    applySidebarState(collapsed);
    localStorage.setItem(SIDEBAR_COLLAPSE_KEY, collapsed ? '1' : '0');
}

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
        } else if (pageId === 'notify-settings') {
            headerTitle.textContent = '邮件提醒配置';
        } else if (pageId === 'placeholder') {
            headerTitle.textContent = '等待增加的模块';
        }
    }
    
    // 如果是用户列表页面，加载数据
    if (pageId === 'customer-list') {
        loadCustomerList();
    }
    
    // 如果是剧头管理页面（从导航栏点击），清除用户筛选
    if (pageId === 'drama-header-management') {
        // 不需要加载数据，等待用户搜索
    }
    
    // 如果是版权方数据页面，加载列表
    if (pageId === 'copyright-management') {
        loadCopyrightList(1);
    }

    // 如果是邮件提醒页面，加载配置与预览
    if (pageId === 'notify-settings' && typeof loadNotifyPageData === 'function') {
        loadNotifyPageData();
    }
}

// 从导航栏点击剧头管理（显示所有剧头）
function showDramaHeaderManagement() {
    currentCustomerId = null;
    currentCustomerCode = null;
    currentCustomerName = '';

    const customerDramaSelectionArea = document.getElementById('customer-drama-selection-area');
    if (customerDramaSelectionArea) {
        customerDramaSelectionArea.classList.add('hidden');
    }
    
    // 重置搜索框为默认状态（显示普通搜索框，隐藏江苏容器）
    const jiangsuContainer = document.getElementById('jiangsu-search-container');
    const normalContainer = document.getElementById('normal-search-container');
    
    if (jiangsuContainer) {
        jiangsuContainer.classList.add('hidden');
    }
    if (normalContainer) {
        normalContainer.classList.remove('hidden');
        const searchInput = document.getElementById('header-search-input');
        if (searchInput) {
            searchInput.placeholder = '';
            searchInput.value = '';
        }
    }
    
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
                    <button onclick="viewCustomerDramas('${customer.customer_code}', '${customer.customer_name.replace(/'/g, "\\'")}')" 
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
function viewCustomerDramas(customerCode, customerName) {
    currentCustomerCode = customerCode;
    currentCustomerName = customerName;
    currentCustomerId = customerCode;  // 兼容旧代码

    customerDramaSelectionState.selectedIds.clear();
    customerDramaSelectionState.allIds = [];
    customerDramaPagingState.page = 1;
    customerDramaPagingState.total = 0;
    customerDramaPagingState.totalPages = 0;
    customerDramaPagingState.keyword = '';
    customerDramaListRendered = false;
    
    console.log('=== viewCustomerDramas ===');
    console.log('customerCode:', customerCode);
    console.log('customerName:', customerName);
    
    // 切换到剧头管理页面
    showPage('drama-header-management');
    
    // 更新标题显示用户名
    const headerTitle = document.getElementById('header-title');
    if (headerTitle) {
        headerTitle.textContent = `${customerName} - 剧头管理`;
    }
    
    // 根据客户类型切换搜索容器
    const jiangsuContainer = document.getElementById('jiangsu-search-container');
    const normalContainer = document.getElementById('normal-search-container');
    
    console.log('jiangsuContainer:', jiangsuContainer);
    console.log('normalContainer:', normalContainer);
    
    // 支持批量搜索的客户列表
    const batchSearchCustomers = ['jiangsu_newmedia', 'xinjiang_telecom'];
    
    if (batchSearchCustomers.includes(customerCode)) {
        console.log(`切换到${customerName}模式 - 显示大文本框`);
        // 江苏新媒体/新疆电信：显示大文本框容器，隐藏单行搜索框容器
        if (jiangsuContainer) {
            jiangsuContainer.classList.remove('hidden');
            console.log('显示批量搜索容器');
            // 清空textarea内容
            const textarea = document.getElementById('header-search-textarea');
            if (textarea) {
                textarea.value = '';
            }
        }
        if (normalContainer) {
            normalContainer.classList.add('hidden');
            console.log('隐藏普通容器');
        }
    } else {
        console.log('切换到其他客户模式 - 显示单行搜索框');
        // 其他客户：隐藏大文本框容器，显示单行搜索框容器
        if (jiangsuContainer) {
            jiangsuContainer.classList.add('hidden');
            console.log('隐藏江苏容器');
        }
        if (normalContainer) {
            normalContainer.classList.remove('hidden');
            console.log('显示普通容器');
            // 清空input内容
            const input = document.getElementById('header-search-input');
            if (input) {
                input.value = '';
            }
        }
    }
    
    // 清空搜索结果
    const resultContainer = document.getElementById('header-search-result');
    if (resultContainer) {
        resultContainer.classList.add('hidden');
        resultContainer.innerHTML = '';
    }
    
    // 隐藏批量选择区域
    const batchSelectionArea = document.getElementById('batch-selection-area');
    if (batchSelectionArea) {
        batchSelectionArea.classList.add('hidden');
    }

    // 自动加载当前省份对应的剧头数据（独立区域，不影响原搜索）
    loadCustomerDramaSelectionList();
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

// ============================================================
// Toast 通知系统
// ============================================================

/**
 * 显示 Toast 通知
 * @param {string} message - 通知消息
 * @param {string} type - 通知类型: 'success' | 'error' | 'warning' | 'info'
 * @param {number} duration - 显示时长（毫秒），默认 3000
 */
function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    // 图标配置
    const icons = {
        success: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>`,
        error: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" x2="9" y1="9" y2="15"/><line x1="9" x2="15" y1="9" y2="15"/></svg>`,
        warning: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>`,
        info: `<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="16" y2="12"/><line x1="12" x2="12.01" y1="8" y2="8"/></svg>`
    };
    
    // 颜色配置
    const colors = {
        success: 'bg-emerald-50 border-emerald-200 text-emerald-800',
        error: 'bg-red-50 border-red-200 text-red-800',
        warning: 'bg-amber-50 border-amber-200 text-amber-800',
        info: 'bg-blue-50 border-blue-200 text-blue-800'
    };
    
    const iconColors = {
        success: 'text-emerald-500',
        error: 'text-red-500',
        warning: 'text-amber-500',
        info: 'text-blue-500'
    };
    
    // 创建 toast 元素
    const toast = document.createElement('div');
    toast.className = `toast flex items-start gap-3 px-4 py-3 rounded-lg border shadow-lg ${colors[type] || colors.info}`;
    toast.innerHTML = `
        <span class="${iconColors[type] || iconColors.info} flex-shrink-0 mt-0.5">${icons[type] || icons.info}</span>
        <p class="text-sm font-medium flex-1">${message}</p>
        <button onclick="closeToast(this.parentElement)" class="flex-shrink-0 opacity-60 hover:opacity-100 transition-opacity">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" x2="6" y1="6" y2="18"/><line x1="6" x2="18" y1="6" y2="18"/></svg>
        </button>
    `;
    
    container.appendChild(toast);
    
    // 自动关闭
    if (duration > 0) {
        setTimeout(() => closeToast(toast), duration);
    }
}

/**
 * 关闭 Toast 通知
 * @param {HTMLElement} toast - toast 元素
 */
function closeToast(toast) {
    if (!toast || toast.classList.contains('toast-exit')) return;
    toast.classList.add('toast-exit');
    setTimeout(() => toast.remove(), 300);
}

// 显示错误消息
function showError(message) {
    showToast(message, 'error', 5000);
}

// 显示成功消息
function showSuccess(message) {
    showToast(message, 'success', 3000);
}

// 显示警告消息
function showWarning(message) {
    showToast(message, 'warning', 4000);
}

// 显示信息消息
function showInfo(message) {
    showToast(message, 'info', 3000);
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
    // 支持批量搜索的客户列表
    const batchSearchCustomers = ['jiangsu_newmedia', 'xinjiang_telecom'];
    
    // 根据客户类型获取搜索关键词
    let keyword = '';
    if (batchSearchCustomers.includes(currentCustomerCode)) {
        keyword = document.getElementById('header-search-textarea')?.value?.trim() || '';
    } else {
        keyword = document.getElementById('header-search-input')?.value?.trim() || '';
    }
    
    const resultContainer = document.getElementById('header-search-result');
    const batchSelectionArea = document.getElementById('batch-selection-area');
    
    if (!keyword) {
        showError('请输入剧集名称进行搜索');
        resultContainer.classList.add('hidden');
        batchSelectionArea.classList.add('hidden');
        return;
    }
    
    // 如果没有选择客户，提示用户
    if (!currentCustomerCode) {
        showError('请先从用户列表选择一个客户');
        return;
    }
    
    // 检查是否是支持批量搜索的客户
    const isBatchCustomer = batchSearchCustomers.includes(currentCustomerCode);
    let dramaNames = [];
    
    if (isBatchCustomer) {
        // 江苏新媒体/新疆电信：按换行分隔
        dramaNames = keyword.split(/\r?\n/).map(name => name.trim()).filter(name => name.length > 0);
    } else {
        // 其他客户：单个剧集
        dramaNames = [keyword];
    }
    
    const isBatchSearch = dramaNames.length > 1;
    
    console.log('=== 批量搜索调试 ===');
    console.log('currentCustomerCode:', currentCustomerCode);
    console.log('isBatchCustomer:', isBatchCustomer);
    console.log('keyword:', keyword);
    console.log('dramaNames:', dramaNames);
    console.log('dramaNames.length:', dramaNames.length);
    console.log('isBatchSearch:', isBatchSearch);
    
    // 如果是支持批量搜索的客户且是批量搜索，显示批量选择界面
    if (isBatchCustomer && isBatchSearch) {
        await showBatchSelectionUI(dramaNames);
        resultContainer.classList.add('hidden');
        return;
    }
    
    // 单个剧集搜索（原有逻辑）
    const singleDramaName = dramaNames[0];
    try {
        // 使用搜索API获取剧集详情，传递customer_code参数
        const response = await fetch(`${API_BASE}/dramas/by-name?name=${encodeURIComponent(singleDramaName)}&customer_code=${encodeURIComponent(currentCustomerCode)}`);
        
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
            batchSelectionArea.classList.add('hidden');
            return;
        }
        
        const result = await response.json();
        
        if (result.code === 200 && result.data) {
            const header = result.data.header;
            const episodes = result.data.episodes || [];
            
            // 保存列配置
            currentDramaColumns = result.data.drama_columns || [];
            currentEpisodeColumns = result.data.episode_columns || [];

            // 江苏新媒体：子集列里有两个“序号”（vod_no剧头序号+vod_info_no子集序号），详情页仅保留子集序号
            if (currentCustomerCode === 'jiangsu_newmedia') {
                currentEpisodeColumns = currentEpisodeColumns.filter(col => col !== 'vod_no');
            }
            
            // 设置当前剧集信息
            // 优先使用API返回的数据库原始ID（用于导出等操作）
            const dbDramaId = result.data.drama_id || header['_db_drama_id'];
            
            // 根据客户类型获取显示用的ID和名称字段
            let idField, nameField;
            if (currentCustomerCode === 'jiangsu_newmedia') {
                // 江苏: sId是数据库ID, seriesName是名称
                idField = 'sId';
                nameField = 'seriesName';
            } else {
                // 其他客户: 第一列是ID, 第二列是名称
                idField = currentDramaColumns[0] || '剧头id';
                nameField = currentDramaColumns[1] || '剧集名称';
            }
            // 使用数据库原始ID（如果有），否则使用显示字段中的ID
            currentDramaId = dbDramaId || header[idField];
            currentDramaName = String(header[nameField] || '');
            currentDramaData = header;
            
            // 在当前页面下方显示详情（使用动态列配置）
            renderDramaDetailInline(header, episodes, resultContainer);
            resultContainer.classList.remove('hidden');
            batchSelectionArea.classList.add('hidden');
        } else {
            resultContainer.innerHTML = `
                <div class="bg-white border border-slate-200 rounded-xl p-8 text-center">
                    <p class="text-slate-500">未找到匹配的剧集</p>
                </div>
            `;
            resultContainer.classList.remove('hidden');
            batchSelectionArea.classList.add('hidden');
        }
    } catch (error) {
        showError('搜索失败：' + error.message);
    }
}

// ==================== 江苏新媒体批量导出功能 ====================

// 批量选择状态
let batchSelectionState = {
    selectedDramas: new Set(),  // 存储选中的剧集名称
    allDramas: []  // 所有可选的剧集
};

// 显示批量选择UI
async function showBatchSelectionUI(dramaNames) {
    const batchSelectionArea = document.getElementById('batch-selection-area');
    const dramaSelectionList = document.getElementById('drama-selection-list');
    const batchExportBtnText = document.getElementById('batch-export-btn-text');
    
    // 根据客户类型更新按钮文本
    if (batchExportBtnText) {
        batchExportBtnText.textContent = `批量导出${currentCustomerName || ''}`;
    }
    
    // 重置状态
    batchSelectionState.selectedDramas.clear();
    batchSelectionState.allDramas = dramaNames;
    
    // 显示加载状态
    dramaSelectionList.innerHTML = `<div class="text-center py-4 text-slate-500">
        <div class="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-2"></div>
        <div>正在加载 ${dramaNames.length} 个剧集信息...</div>
    </div>`;
    batchSelectionArea.classList.remove('hidden');
    
    // 使用批量查询API（性能优化）
    try {
        const response = await fetch(`${API_BASE}/dramas/batch-query`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                drama_names: dramaNames,
                customer_code: currentCustomerCode
            })
        });
        
        if (!response.ok) {
            throw new Error('批量查询失败');
        }
        
        const result = await response.json();
        
        if (result.code !== 200 || !result.data || !result.data.results) {
            throw new Error('返回数据格式错误');
        }
        
        const dramaInfos = result.data.results;
        
        // 渲染剧集列表（带详细信息）
        dramaSelectionList.innerHTML = dramaInfos.map((info, index) => {
            if (!info.found) {
                return `
                    <div class="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <input type="checkbox" id="drama-checkbox-${index}" value="${info.name}" disabled
                            class="w-4 h-4 text-slate-400 border-slate-300 rounded opacity-50 cursor-not-allowed">
                        <div class="flex-1">
                            <div class="text-slate-900 font-medium">${info.name}</div>
                            <div class="text-xs text-red-600 mt-1">❌ 未找到该剧集</div>
                        </div>
                    </div>
                `;
            }
            
            const dramaId = info.drama_id || '';
            const episodeCount = info.episode_count || 0;
            const description = info.description || '';
            const shortDesc = description.length > 50 ? description.substring(0, 50) + '...' : description;
            
            return `
                <div class="flex items-start gap-3 p-3 bg-slate-50 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200">
                    <input type="checkbox" id="drama-checkbox-${index}" value="${info.name}" 
                        onchange="toggleDramaSelection('${info.name.replace(/'/g, "\\'")}')"
                        class="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 mt-1">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-slate-900 font-semibold">${info.name}</span>
                            <span class="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">ID: ${dramaId}</span>
                        </div>
                        <div class="flex items-center gap-3 text-xs text-slate-600">
                            <span class="flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>
                                    <line x1="3" x2="21" y1="9" y2="9"/>
                                    <line x1="9" x2="9" y1="21" y2="9"/>
                                </svg>
                                ${episodeCount} 集
                            </span>
                            ${shortDesc ? `<span class="text-slate-500 truncate" title="${description}">${shortDesc}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // 显示统计信息
        const foundCount = result.data.found;
        const notFoundCount = result.data.not_found;
        if (notFoundCount > 0) {
            showSuccess(`加载完成：找到 ${foundCount} 个剧集，${notFoundCount} 个未找到`);
        }
        
        // 更新选中计数
        updateSelectedCount();
        
    } catch (error) {
        dramaSelectionList.innerHTML = `
            <div class="text-center py-4 text-red-500">
                加载失败：${error.message}
            </div>
        `;
        showError('加载剧集信息失败：' + error.message);
    }
}

// 切换剧集选择状态
function toggleDramaSelection(dramaName) {
    if (batchSelectionState.selectedDramas.has(dramaName)) {
        batchSelectionState.selectedDramas.delete(dramaName);
    } else {
        batchSelectionState.selectedDramas.add(dramaName);
    }
    updateSelectedCount();
}

// 更新选中计数
function updateSelectedCount() {
    const count = batchSelectionState.selectedDramas.size;
    const countElement = document.getElementById('selected-count');
    const exportBtn = document.getElementById('batch-export-btn');
    
    if (countElement) {
        countElement.textContent = `已选择 ${count} 个`;
    }
    
    // 启用/禁用导出按钮
    if (exportBtn) {
        exportBtn.disabled = count === 0;
    }
}

// 全选剧集
function selectAllDramas() {
    batchSelectionState.allDramas.forEach(name => {
        batchSelectionState.selectedDramas.add(name);
    });
    
    // 更新所有复选框状态
    batchSelectionState.allDramas.forEach((name, index) => {
        const checkbox = document.getElementById(`drama-checkbox-${index}`);
        if (checkbox) {
            checkbox.checked = true;
        }
    });
    
    updateSelectedCount();
}

// 清空所有选择
function clearAllSelections() {
    batchSelectionState.selectedDramas.clear();
    
    // 更新所有复选框状态
    batchSelectionState.allDramas.forEach((name, index) => {
        const checkbox = document.getElementById(`drama-checkbox-${index}`);
        if (checkbox) {
            checkbox.checked = false;
        }
    });
    
    updateSelectedCount();
}

// 处理Excel文件上传
async function handleExcelUpload(event) {
    const file = event.target.files[0];
    if (!file) {
        return;
    }
    
    // 检查文件类型
    const fileName = file.name.toLowerCase();
    if (!fileName.endsWith('.xlsx') && !fileName.endsWith('.xls')) {
        showError('请上传Excel文件（.xlsx 或 .xls）');
        event.target.value = '';
        return;
    }
    
    // 显示批量选择区域和加载状态
    const batchSelectionArea = document.getElementById('batch-selection-area');
    const dramaSelectionList = document.getElementById('drama-selection-list');
    const batchExportBtnText = document.getElementById('batch-export-btn-text');
    
    // 根据客户类型更新按钮文本
    if (batchExportBtnText) {
        batchExportBtnText.textContent = `批量导出${currentCustomerName || ''}`;
    }
    
    batchSelectionArea.classList.remove('hidden');
    dramaSelectionList.innerHTML = `<div class="text-center py-8 text-slate-500">
        <div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mb-4"></div>
        <div class="text-lg font-medium">正在读取Excel并查询剧集信息...</div>
        <div class="text-sm mt-2">请稍候，这可能需要几秒钟</div>
    </div>`;
    
    try {
        // 读取文件为二进制数据
        const fileData = await file.arrayBuffer();
        
        // 调用后端一体化API：解析Excel + 批量查询
        const response = await fetch(`${API_BASE}/dramas/import-and-query-excel?customer_code=${encodeURIComponent(currentCustomerCode)}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/octet-stream'
            },
            body: fileData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || '处理失败');
        }
        
        const result = await response.json();
        
        if (result.code !== 200 || !result.data || !result.data.results) {
            throw new Error('返回数据格式错误');
        }
        
        // 重置批量选择状态
        const dramaNames = result.data.results.map(r => r.name);
        batchSelectionState.selectedDramas.clear();
        batchSelectionState.allDramas = dramaNames;
        
        const dramaInfos = result.data.results;
        
        // 渲染剧集列表
        dramaSelectionList.innerHTML = dramaInfos.map((info, index) => {
            if (!info.found) {
                return `
                    <div class="flex items-center gap-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                        <input type="checkbox" id="drama-checkbox-${index}" value="${info.name}" disabled
                            class="w-4 h-4 text-slate-400 border-slate-300 rounded opacity-50 cursor-not-allowed">
                        <div class="flex-1">
                            <div class="text-slate-900 font-medium">${info.name}</div>
                            <div class="text-xs text-red-600 mt-1">❌ 未找到该剧集</div>
                        </div>
                    </div>
                `;
            }
            
            const dramaId = info.drama_id || '';
            const episodeCount = info.episode_count || 0;
            const description = info.description || '';
            const shortDesc = description.length > 50 ? description.substring(0, 50) + '...' : description;
            
            return `
                <div class="flex items-start gap-3 p-3 bg-slate-50 hover:bg-slate-100 rounded-lg transition-colors border border-slate-200">
                    <input type="checkbox" id="drama-checkbox-${index}" value="${info.name}" 
                        onchange="toggleDramaSelection('${info.name.replace(/'/g, "\\'")}')"
                        class="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500 mt-1">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="text-slate-900 font-semibold">${info.name}</span>
                            <span class="px-2 py-0.5 bg-blue-100 text-blue-700 text-xs font-medium rounded">ID: ${dramaId}</span>
                        </div>
                        <div class="flex items-center gap-3 text-xs text-slate-600">
                            <span class="flex items-center gap-1">
                                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                    <rect width="18" height="18" x="3" y="3" rx="2" ry="2"/>
                                    <line x1="3" x2="21" y1="9" y2="9"/>
                                    <line x1="9" x2="9" y1="21" y2="9"/>
                                </svg>
                                ${episodeCount} 集
                            </span>
                            ${shortDesc ? `<span class="text-slate-500 truncate" title="${description}">${shortDesc}</span>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // 清空文件选择
        event.target.value = '';
        
        // 显示统计信息
        const foundCount = result.data.found;
        const notFoundCount = result.data.not_found;
        const totalCount = result.data.total;
        
        showSuccess(`成功导入 ${totalCount} 个剧集（识别列：${result.data.column_name}）：找到 ${foundCount} 个，未找到 ${notFoundCount} 个`);
        
        // 更新选中计数
        updateSelectedCount();
        
    } catch (error) {
        dramaSelectionList.innerHTML = `
            <div class="text-center py-8">
                <div class="text-red-500 text-lg font-medium mb-2">❌ 加载失败</div>
                <div class="text-slate-600">${error.message}</div>
            </div>
        `;
        showError('Excel导入失败：' + error.message);
        event.target.value = '';
    }
}

// 通用批量导出函数 - 根据当前客户类型调用对应API
async function exportBatch() {
    const selectedDramas = Array.from(batchSelectionState.selectedDramas);
    
    if (selectedDramas.length === 0) {
        showError('请至少选择一个剧集');
        return;
    }
    
    // 获取客户对应的API端点和名称
    const customerApiMap = {
        'jiangsu_newmedia': { endpoint: 'jiangsu_newmedia', name: '江苏新媒体' },
        'xinjiang_telecom': { endpoint: 'xinjiang_telecom', name: '新疆电信' }
    };
    
    const customerInfo = customerApiMap[currentCustomerCode];
    if (!customerInfo) {
        showError(`当前客户 ${currentCustomerName || currentCustomerCode} 不支持批量导出`);
        return;
    }
    
    try {
        // 禁用按钮，显示加载状态
        const exportBtn = document.getElementById('batch-export-btn');
        exportBtn.disabled = true;
        exportBtn.innerHTML = `
            <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>导出中...</span>
        `;
        
        // 调用批量导出API
        const response = await fetch(`${API_BASE}/dramas/export/batch/${customerInfo.endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                drama_names: selectedDramas
            })
        });
        
        if (response.ok) {
            // 下载文件
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // 生成文件名
            let filename;
            if (selectedDramas.length === 1) {
                filename = `${customerInfo.name}_${selectedDramas[0]}_注入表.xlsx`;
            } else {
                filename = `${customerInfo.name}_批量导出_${selectedDramas.length}个剧集.xlsx`;
            }
            a.download = filename;
            
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            showSuccess(`成功导出 ${selectedDramas.length} 个剧集！`);
        } else {
            const result = await response.json();
            showError('导出失败：' + (result.detail || '未知错误'));
        }
    } catch (error) {
        showError('导出失败：' + error.message);
    } finally {
        // 恢复按钮状态
        const exportBtn = document.getElementById('batch-export-btn');
        const batchExportBtnText = document.getElementById('batch-export-btn-text');
        exportBtn.disabled = false;
        exportBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" x2="12" y1="15" y2="3"/>
            </svg>
            <span id="batch-export-btn-text">批量导出${currentCustomerName || ''}</span>
        `;
    }
}

// 批量导出江苏新媒体 (兼容旧调用，内部调用通用函数)
async function exportJiangsuBatch() {
    await exportBatch();
}

// 在剧头管理页面内联显示剧集详情（支持动态列配置）
function renderDramaDetailInline(header, episodes, container) {
    // 江苏字段名中英文映射
    const jiangsuFieldMap = {
        'vod_no': '序号',
        'sId': '剧头ID',
        'appId': '应用ID',
        'seriesName': '剧集名称',
        'volumnCount': '集数',
        'description': '简介',
        'seriesFlag': '剧头类型',
        'sortName': '搜索关键字',
        'programType': '栏目类型',
        'releaseYear': '上映年份',
        'language': '语言',
        'rating': '评分',
        'originalCountry': '国家',
        'pgmCategory': '分类',
        'pgmSedClass': '二级分类',
        'director': '导演',
        'actorDisplay': '演员',
        'vod_info_no': '序号',
        'pId': '子集ID',
        'programName': '节目名称',
        'type': '类型',
        'fileURL': '文件地址',
        'duration': '时长',
        'bitRateType': '比特率',
        'mediaSpec': '视音频参数'
    };
    
    // 获取字段显示名称
    const getDisplayName = (fieldName) => {
        if (currentCustomerCode === 'jiangsu_newmedia' && jiangsuFieldMap[fieldName]) {
            return jiangsuFieldMap[fieldName];
        }
        return fieldName;
    };

    const isImageField = (fieldName, displayName, value) => {
        const label = `${fieldName || ''}${displayName || ''}`;
        const lowerValue = String(value || '').toLowerCase();
        return /图|海报|图片/.test(label) || /\.(jpg|jpeg|png|webp|gif|bmp)$/i.test(lowerValue);
    };
    
    // 根据客户类型获取正确的ID和名称字段（用于显示）
    let idField, nameField;
    if (currentCustomerCode === 'jiangsu_newmedia') {
        idField = 'sId';
        nameField = 'seriesName';
    } else {
        idField = currentDramaColumns[0] || '剧头id';
        nameField = currentDramaColumns[1] || '剧集名称';
    }
    const displayDramaId = header[idField] || '';
    const dramaName = String(header[nameField] || '');
    // 使用全局变量 currentDramaId（数据库原始ID）用于导出操作
    const exportDramaId = currentDramaId || header['_db_drama_id'] || displayDramaId;
    
    let html = '<div class="space-y-6">';
    
    // 剧集基本信息卡片
    html += '<div class="bg-gradient-to-br from-white to-slate-50 border border-slate-200 rounded-xl p-6 shadow-lg">';
    html += '<div class="flex items-center justify-between mb-6 pb-4 border-b border-slate-200">';
    html += '<div class="flex items-center gap-3">';
    html += '<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center text-white font-bold text-xl shadow-lg">';
    html += (dramaName && dramaName.length > 0 ? dramaName.charAt(0) : '剧');
    html += '</div>';
    html += '<div><h3 class="text-xl font-bold text-slate-900">' + dramaName + '</h3>';
    html += '<p class="text-sm text-slate-500 mt-1">' + getDisplayName(idField) + ': ' + displayDramaId + ' | ' + currentCustomerName + '</p></div>';
    html += '</div>';
    html += '<div class="flex items-center gap-2">';
    html += `<button onclick="exportDramaById(${exportDramaId})" 
        class="text-green-600 hover:text-green-700 font-medium text-sm inline-flex items-center gap-1.5 bg-green-50 hover:bg-green-100 border border-green-200 hover:border-green-300 px-3 py-1.5 rounded-lg transition-all">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" x2="12" y1="15" y2="3"/>
        </svg>
        导出Excel
    </button>`;
    html += '</div></div>';
    
    // 基本信息网格 - 使用动态列配置（跳过序号、ID和名称字段）
    html += '<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">';
    // 跳过序号、ID、名称等字段
    const skipFields = currentCustomerCode === 'jiangsu_newmedia' 
        ? ['vod_no', 'sId', 'seriesName'] 
        : currentDramaColumns.slice(0, 2);
    const displayFields = currentDramaColumns.filter(f => !skipFields.includes(f));
    
    displayFields.forEach(fieldName => {
        const value = header[fieldName] !== null && header[fieldName] !== undefined ? header[fieldName] : '-';
        // 对于URL类型的字段，显示为链接
        const isUrl = String(value).startsWith('http') || String(value).startsWith('ftp') || String(value).startsWith('/');
        const displayName = getDisplayName(fieldName);
        const isImage = isImageField(fieldName, displayName, value);
        let displayValue = value;
        if (isImage && value !== '-') {
            const shortValue = value.length > 40 ? value.substring(0, 40) + '...' : value;
            displayValue = `<a href="${value}" target="_blank" class="text-blue-600 hover:underline text-xs truncate block" title="${value}">${shortValue}</a>`;
        } else if (isUrl) {
            displayValue = `<a href="${value}" target="_blank" class="text-blue-600 hover:underline text-xs truncate block" title="${value}">${value}</a>`;
        }
        
        html += `<div class="bg-white border border-slate-200 rounded-lg p-3">
            <div class="text-xs font-medium text-slate-500 mb-1">${displayName}</div>
            <div class="text-sm font-semibold text-slate-900 truncate" title="${value}">${displayValue}</div>
        </div>`;
    });
    html += '</div>';
    html += '</div>';
    
    // 子集信息
    html += '<div class="bg-gradient-to-br from-white to-indigo-50 border border-slate-200 rounded-xl p-6 shadow-lg">';
    html += '<div class="flex items-center justify-between mb-4 pb-4 border-b border-slate-200">';
    html += '<h3 class="text-lg font-bold text-slate-900">子集信息 (' + episodes.length + ' 集)</h3>';
    html += '</div>';
    
    if (episodes.length > 0) {
        html += '<div class="overflow-x-auto"><table class="w-full text-left text-sm">';
        html += '<thead><tr class="bg-slate-100 border-b border-slate-200">';
        
        // 使用动态列配置生成表头（显示中文名称）
        currentEpisodeColumns.forEach(colName => {
            html += `<th class="px-4 py-2 font-semibold text-slate-700 whitespace-nowrap">${getDisplayName(colName)}</th>`;
        });
        html += '</tr></thead><tbody>';
        
        episodes.forEach((ep, index) => {
            const rowClass = index % 2 === 0 ? 'bg-white' : 'bg-slate-50/50';
            html += `<tr class="${rowClass} border-b border-slate-100 hover:bg-blue-50/50">`;
            
            // 使用动态列配置生成单元格
            currentEpisodeColumns.forEach(colName => {
                let value = ep[colName];
                if (value === null || value === undefined) value = '-';
                
                // 对于URL类型的字段，显示为链接
                const isUrl = String(value).startsWith('http') || String(value).startsWith('ftp');
                const displayName = getDisplayName(colName);
                const isImage = isImageField(colName, displayName, value);
                if (isUrl || isImage) {
                    const linkText = value.length > 40 ? value.substring(0, 40) + '...' : value;
                    html += `<td class="px-4 py-2"><a href="${value}" target="_blank" class="text-blue-600 hover:text-blue-700 hover:underline text-xs font-mono truncate max-w-xs inline-block" title="${value}">${linkText}</a></td>`;
                } else {
                    html += `<td class="px-4 py-2 text-slate-600 whitespace-nowrap">${value}</td>`;
                }
            });
            
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

// ==================== 剧头管理页剧头勾选导出（独立，不影响原搜索） ====================

let customerDramaSelectionState = {
    selectedIds: new Set(),
    allIds: []
};

let customerDramaListRendered = false;

let customerDramaPagingState = {
    page: 1,
    pageSize: 10,
    total: 0,
    totalPages: 0,
    keyword: ''
};

function _escapeHtml(text) {
    return String(text ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

function _formatDisplayDateTime(value) {
    if (!value) return '-';
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    const pad = (n) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function _extractDramaKeyword() {
    return (document.getElementById('header-search-input')?.value || '').trim();
}

function updateCustomerDramaPagingUI() {
    const pageInfo = document.getElementById('customer-drama-page-info');
    const prevBtn = document.getElementById('customer-drama-prev-btn');
    const nextBtn = document.getElementById('customer-drama-next-btn');

    const page = customerDramaPagingState.page;
    const totalPages = Math.max(1, customerDramaPagingState.totalPages || 1);
    const total = customerDramaPagingState.total || 0;

    if (pageInfo) {
        pageInfo.textContent = `第 ${page} / ${totalPages} 页，共 ${total} 条`;
    }
    if (prevBtn) {
        prevBtn.disabled = page <= 1;
    }
    if (nextBtn) {
        nextBtn.disabled = page >= totalPages;
    }
}

async function loadCustomerDramaSelectionList(keyword = undefined, page = undefined) {
    if (!currentCustomerCode) {
        return;
    }

    if (keyword !== undefined) {
        customerDramaPagingState.keyword = keyword;
    }
    if (page !== undefined) {
        customerDramaPagingState.page = page;
    }

    const effectiveKeyword = customerDramaPagingState.keyword || '';
    const effectivePage = customerDramaPagingState.page || 1;

    const resultContainer = document.getElementById('header-search-result');
    if (resultContainer) {
        resultContainer.classList.add('hidden');
        resultContainer.innerHTML = '';
    }

    const selectionArea = document.getElementById('customer-drama-selection-area');
    const tableBody = document.getElementById('customer-drama-table-body');
    if (!selectionArea || !tableBody) {
        return;
    }

    selectionArea.classList.remove('hidden');
    if (!customerDramaListRendered) {
        tableBody.innerHTML = '<tr><td colspan="5" class="px-6 py-8 text-center text-slate-500">正在加载剧头数据...</td></tr>';
    }
    updateCustomerDramaPagingUI();

    try {
        const url = new URL(`${API_BASE}/dramas/selection/by-customer`, window.location.origin);
        url.searchParams.set('customer_code', currentCustomerCode);
        url.searchParams.set('page', String(effectivePage));
        url.searchParams.set('page_size', String(customerDramaPagingState.pageSize));
        if (effectiveKeyword) {
            url.searchParams.set('keyword', effectiveKeyword);
        }

        const response = await fetch(url.toString());
        const result = await response.json();
        if (!response.ok || result.code !== 200) {
            throw new Error(result.detail || result.message || '加载失败');
        }

        const rows = result.data?.list || [];
        customerDramaPagingState.total = Number(result.data?.total || 0);
        customerDramaPagingState.totalPages = Number(result.data?.total_pages || 0);
        customerDramaPagingState.page = Number(result.data?.page || effectivePage);
        customerDramaSelectionState.allIds = rows.map(row => String(row.drama_id));
        updateCustomerDramaPagingUI();

        if (rows.length === 0) {
            tableBody.innerHTML = '<tr><td colspan="5" class="px-6 py-8 text-center text-slate-500">当前省份暂无剧头数据</td></tr>';
            updateCustomerDramaSelectedCount();
            return;
        }

        tableBody.innerHTML = rows.map((row, index) => {
            const rowClass = index % 2 === 0 ? 'bg-white' : 'bg-slate-50/30';
            const dramaId = _escapeHtml(String(row.drama_id || ''));
            const dramaName = _escapeHtml(String(row.drama_name || '-'));
            const episodeCount = _escapeHtml(String(row.episode_count ?? 0));
            const createdAt = _escapeHtml(_formatDisplayDateTime(row.created_at));

            return `
                <tr class="${rowClass} hover:bg-blue-50/50 transition-all duration-200 border-b border-slate-100 group">
                    <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">
                        <input type="checkbox" id="customer-drama-checkbox-${index}" value="${dramaId}"
                            onchange="toggleCustomerDramaSelection('${dramaId}')"
                            ${customerDramaSelectionState.selectedIds.has(String(row.drama_id)) ? 'checked' : ''}
                            class="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500">
                    </td>
                    <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${dramaId || '-'}</td>
                    <td class="px-4 py-3 text-sm font-medium text-slate-900 whitespace-nowrap">${dramaName}</td>
                    <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${episodeCount}</td>
                    <td class="px-4 py-3 text-sm text-slate-600 whitespace-nowrap">${createdAt}</td>
                </tr>
            `;
        }).join('');

        customerDramaListRendered = true;
        updateCustomerDramaSelectedCount();
    } catch (error) {
        tableBody.innerHTML = `<tr><td colspan="5" class="px-6 py-8 text-center text-red-500">加载失败：${_escapeHtml(error.message)}</td></tr>`;
        showError('加载剧头数据失败：' + error.message);
    }
}

function prevCustomerDramaPage(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    if (customerDramaPagingState.page <= 1) {
        return;
    }
    loadCustomerDramaSelectionList(undefined, customerDramaPagingState.page - 1);
}

function nextCustomerDramaPage(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const totalPages = Math.max(1, customerDramaPagingState.totalPages || 1);
    if (customerDramaPagingState.page >= totalPages) {
        return;
    }
    loadCustomerDramaSelectionList(undefined, customerDramaPagingState.page + 1);
}

function toggleCustomerDramaSelection(dramaId) {
    if (customerDramaSelectionState.selectedIds.has(dramaId)) {
        customerDramaSelectionState.selectedIds.delete(dramaId);
    } else {
        customerDramaSelectionState.selectedIds.add(dramaId);
    }
    updateCustomerDramaSelectedCount();
}

function updateCustomerDramaSelectedCount() {
    const count = customerDramaSelectionState.selectedIds.size;
    const countElement = document.getElementById('drama-selected-count');
    const exportBtn = document.getElementById('customer-drama-export-btn');

    if (countElement) {
        countElement.textContent = `已选择 ${count} 个`;
    }
    if (exportBtn) {
        exportBtn.disabled = count === 0;
    }
}

function selectAllCustomerDramaRows() {
    customerDramaSelectionState.allIds.forEach(id => customerDramaSelectionState.selectedIds.add(id));
    customerDramaSelectionState.allIds.forEach((id, index) => {
        const checkbox = document.getElementById(`customer-drama-checkbox-${index}`);
        if (checkbox) checkbox.checked = true;
    });
    updateCustomerDramaSelectedCount();
}

function clearAllCustomerDramaSelections() {
    customerDramaSelectionState.selectedIds.clear();
    customerDramaSelectionState.allIds.forEach((id, index) => {
        const checkbox = document.getElementById(`customer-drama-checkbox-${index}`);
        if (checkbox) checkbox.checked = false;
    });
    updateCustomerDramaSelectedCount();
}

async function exportSelectedCustomerDramas() {
    if (!currentCustomerCode) {
        showError('请先从用户列表选择一个客户');
        return;
    }

    const selectedIds = Array.from(customerDramaSelectionState.selectedIds);
    if (selectedIds.length === 0) {
        showError('请至少选择一个剧头');
        return;
    }

    const exportBtn = document.getElementById('customer-drama-export-btn');
    if (!exportBtn) {
        return;
    }

    let successCount = 0;
    const failedIds = [];

    try {
        exportBtn.disabled = true;
        exportBtn.innerHTML = `
            <svg class="animate-spin h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            <span>逐个导出中...</span>
        `;

        for (const dramaId of selectedIds) {
            try {
                const response = await fetch(`${API_BASE}/dramas/${encodeURIComponent(dramaId)}/export`);
                if (!response.ok) {
                    throw new Error('导出失败');
                }

                const blob = await response.blob();
                const downloadUrl = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = downloadUrl;

                const disposition = response.headers.get('Content-Disposition') || '';
                const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
                const normalMatch = disposition.match(/filename="?([^";]+)"?/i);
                let filename = `${currentCustomerName || currentCustomerCode}_${dramaId}.xlsx`;
                if (utf8Match && utf8Match[1]) {
                    filename = decodeURIComponent(utf8Match[1]);
                } else if (normalMatch && normalMatch[1]) {
                    filename = normalMatch[1];
                }
                a.download = filename;

                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(downloadUrl);
                document.body.removeChild(a);

                successCount += 1;
            } catch (_err) {
                failedIds.push(dramaId);
            }
        }

        if (failedIds.length === 0) {
            showSuccess(`成功导出 ${successCount} 个剧集文件`);
        } else {
            showWarning(`成功 ${successCount} 个，失败 ${failedIds.length} 个（ID: ${failedIds.join(', ')}）`);
        }
    } catch (error) {
        showError('导出失败：' + error.message);
    } finally {
        exportBtn.disabled = false;
        exportBtn.innerHTML = `
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="7 10 12 15 17 10"/>
                <line x1="12" x2="12" y1="15" y2="3"/>
            </svg>
            <span id="customer-drama-export-btn-text">逐个导出选中剧头</span>
        `;
    }
}

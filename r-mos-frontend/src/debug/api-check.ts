/**
 * API 冒烟测试脚本
 * 
 * 用于验证 Phase 1-3 的 Data Layer 正确性
 * 运行方式：在浏览器控制台或使用 ts-node 执行
 * 
 * 测试项：
 * 1. Health Check API
 * 2. SOP List API
 * 3. Task API (get)
 * 4. Adapter Info API
 */

const API_BASE = 'http://localhost:8000/api/v1';

interface HealthResponse {
    status: string;
    timestamp: string;
    version: string;
    checks: {
        adapter: { status: string; message: string };
        system: { status: string; message: string };
    };
}

interface SOPListItem {
    id: number;
    name: string;
    category?: string;
    difficulty_level: string;
}

interface Task {
    id: number;
    title: string;
    status: string;
    sop_id?: number;
}

// 测试结果收集
const results: { test: string; passed: boolean; message: string }[] = [];

async function testHealthCheck(): Promise<void> {
    console.log('\n🔍 测试 1: Health Check API');
    try {
        const response = await fetch(`${API_BASE}/health`);
        const data: HealthResponse = await response.json();

        if (data.status === 'healthy') {
            results.push({ test: 'Health Check', passed: true, message: `✅ 服务健康 - v${data.version}` });
            console.log(`  ✅ 状态: ${data.status}`);
            console.log(`  ✅ 版本: ${data.version}`);
            console.log(`  ✅ Adapter: ${data.checks.adapter.status} - ${data.checks.adapter.message}`);
        } else {
            results.push({ test: 'Health Check', passed: false, message: `❌ 状态异常: ${data.status}` });
        }
    } catch (error) {
        results.push({ test: 'Health Check', passed: false, message: `❌ 请求失败: ${error}` });
        console.error('  ❌ 请求失败:', error);
    }
}

async function testSOPListAPI(): Promise<void> {
    console.log('\n🔍 测试 2: SOP List API');
    try {
        const response = await fetch(`${API_BASE}/sops?skip=0&limit=10`);
        const data: SOPListItem[] = await response.json();

        if (Array.isArray(data) && data.length > 0) {
            results.push({ test: 'SOP List', passed: true, message: `✅ 返回 ${data.length} 条 SOP` });
            console.log(`  ✅ 返回 ${data.length} 条 SOP`);
            data.slice(0, 3).forEach((sop, i) => {
                console.log(`     ${i + 1}. [${sop.id}] ${sop.name} (${sop.difficulty_level})`);
            });
        } else if (Array.isArray(data)) {
            results.push({ test: 'SOP List', passed: true, message: '⚠️ 返回空列表' });
            console.log('  ⚠️ 返回空列表');
        } else {
            results.push({ test: 'SOP List', passed: false, message: `❌ 响应格式异常` });
            console.log('  ❌ 响应格式异常:', data);
        }
    } catch (error) {
        results.push({ test: 'SOP List', passed: false, message: `❌ 请求失败: ${error}` });
        console.error('  ❌ 请求失败:', error);
    }
}

async function testTaskGetAPI(): Promise<void> {
    console.log('\n🔍 测试 3: Task Get API');
    try {
        // 尝试获取 ID=1 的任务
        const response = await fetch(`${API_BASE}/tasks/1`);

        if (response.ok) {
            const data: Task = await response.json();
            results.push({ test: 'Task Get', passed: true, message: `✅ 获取任务成功: ${data.title}` });
            console.log(`  ✅ 任务 ID: ${data.id}`);
            console.log(`  ✅ 标题: ${data.title}`);
            console.log(`  ✅ 状态: ${data.status}`);
            console.log(`  ✅ SOP ID: ${data.sop_id ?? 'NULL'}`);
        } else if (response.status === 404) {
            results.push({ test: 'Task Get', passed: true, message: '⚠️ 任务不存在 (404) - API 正常工作' });
            console.log('  ⚠️ 任务 ID=1 不存在 (404) - API 端点正常工作');
        } else {
            results.push({ test: 'Task Get', passed: false, message: `❌ 状态码: ${response.status}` });
            console.log(`  ❌ 响应状态码: ${response.status}`);
        }
    } catch (error) {
        results.push({ test: 'Task Get', passed: false, message: `❌ 请求失败: ${error}` });
        console.error('  ❌ 请求失败:', error);
    }
}

async function testAdapterInfoAPI(): Promise<void> {
    console.log('\n🔍 测试 4: Adapter Info API');
    try {
        const response = await fetch(`${API_BASE}/adapter/info`);
        const data = await response.json();

        if (response.ok && data.robot_id) {
            results.push({ test: 'Adapter Info', passed: true, message: `✅ 机器人: ${data.robot_id}` });
            console.log(`  ✅ 机器人 ID: ${data.robot_id}`);
            console.log(`  ✅ 型号: ${data.model}`);
            console.log(`  ✅ 固件版本: ${data.firmware_version}`);
            console.log(`  ✅ 运行状态: ${data.runtime_status}`);
        } else {
            results.push({ test: 'Adapter Info', passed: false, message: `❌ 响应异常` });
            console.log('  ❌ 响应异常:', data);
        }
    } catch (error) {
        results.push({ test: 'Adapter Info', passed: false, message: `❌ 请求失败: ${error}` });
        console.error('  ❌ 请求失败:', error);
    }
}

async function testFaultCasesAPI(): Promise<void> {
    console.log('\n🔍 测试 5: Fault Cases API');
    try {
        const response = await fetch(`${API_BASE}/fault-cases`);
        const data = await response.json();

        if (data.items && Array.isArray(data.items)) {
            results.push({ test: 'Fault Cases', passed: true, message: `✅ 返回 ${data.total} 条故障案例` });
            console.log(`  ✅ 总数: ${data.total}`);
            console.log(`  ✅ 返回条数: ${data.items.length}`);
            data.items.slice(0, 3).forEach((fault: any, i: number) => {
                console.log(`     ${i + 1}. [${fault.fault_code}] ${fault.name} (${fault.severity})`);
            });
        } else {
            results.push({ test: 'Fault Cases', passed: false, message: `❌ 响应格式异常` });
            console.log('  ❌ 响应格式异常:', data);
        }
    } catch (error) {
        results.push({ test: 'Fault Cases', passed: false, message: `❌ 请求失败: ${error}` });
        console.error('  ❌ 请求失败:', error);
    }
}

// 主函数
async function runAPICheck(): Promise<void> {
    console.log('╔═══════════════════════════════════════════════════════════╗');
    console.log('║        R-MOS Phase 1-3 API 冒烟测试 (Data Layer)          ║');
    console.log('╚═══════════════════════════════════════════════════════════╝');
    console.log(`\n🌐 API Base: ${API_BASE}`);
    console.log(`📅 测试时间: ${new Date().toLocaleString()}`);

    await testHealthCheck();
    await testSOPListAPI();
    await testTaskGetAPI();
    await testAdapterInfoAPI();
    await testFaultCasesAPI();

    // 汇总结果
    console.log('\n═══════════════════════════════════════════════════════════');
    console.log('📊 测试结果汇总');
    console.log('═══════════════════════════════════════════════════════════');

    const passed = results.filter(r => r.passed).length;
    const total = results.length;

    results.forEach(r => {
        console.log(`  ${r.passed ? '✅' : '❌'} ${r.test}: ${r.message}`);
    });

    console.log(`\n📈 通过率: ${passed}/${total} (${Math.round(passed / total * 100)}%)`);

    if (passed === total) {
        console.log('\n🎉 所有测试通过！Data Layer 审计完成。');
    } else {
        console.log('\n⚠️ 部分测试未通过，请检查上述错误。');
    }
}

// 导出供外部调用
export { runAPICheck };

// 如果在 Node.js 环境中直接运行
if (typeof window === 'undefined') {
    runAPICheck().catch(console.error);
}

// ==================== pet-care-claw.js 主入口 ====================
// 功能：宠物照护技能总调度入口
// 版本：1.0.0
import {Command} from 'commander';

// ==================== 引入子技能模块 ====================
import {getPetStatus, getPetDevices} from './pet-status-query.js';
import {controlFeeder, triggerFeeding} from './feeder-control.js';
import {fetchPetBriefData, generatePetBriefData} from './pet-environment-brief.js';
import {fetchPetCareData} from './pet-care-data-collector.js';

// ==================== 常量配置 ====================
const PROGRAM_NAME = 'pet-care-claw';
const VERSION = '1.0.0';
const DEFAULT_SKILL_ID = 'petCare';

// ==================== 核心调度函数 ====================
async function callPetCareClaw(tools, skillId, verbose = false) {
    const output = [];

    for (const tool of tools) {
        if (verbose) console.error(`[verbose] 执行工具：${tool.name}`);

        try {
            let data;

            switch (tool.name) {
                case 'get_pet_status':
                    data = await getPetStatus(verbose);
                    break;

                case 'get_pet_devices':
                    data = await getPetDevices(verbose);
                    break;

                case 'control_feeder':
                    data = await controlFeeder(
                        tool.args?.deviceId,
                        tool.args?.portionSize || 20,
                        verbose
                    );
                    break;

                case 'trigger_feeding':
                    data = await triggerFeeding(
                        tool.args?.deviceId,
                        tool.args?.prodId,
                        tool.args?.portionSize || 20,
                        verbose
                    );
                    break;

                case 'get_pet_brief':
                    data = await fetchPetBriefData(verbose);
                    break;

                case 'get_pet_care_data':
                    data = await fetchPetCareData(verbose);
                    break;

                default:
                    console.error(`[warning] 未知工具：${tool.name}`);
                    continue;
            }

            output.push({tool: tool.name, data});
        } catch (err) {
            console.error(`[error] ${tool.name} 执行失败：${err.message}`);
            throw err;
        }
    }

    console.log(JSON.stringify(output, null, 2));
}

// ==================== 命令注册 ====================
function registerClawCommands(program) {
    // 宠物状态查询
    program.command('get_pet_status')
        .description('获取宠物状态全景（猫砂盆、喂食器、温度、位置）')
        .option('--skill-id <id>', DEFAULT_SKILL_ID)
        .option('--verbose')
        .action(async (opts) => {
            await callPetCareClaw([{name: 'get_pet_status', args: opts}], opts.skillId, opts.verbose);
        });

    // 宠物设备列表
    program.command('get_pet_devices')
        .description('获取宠物相关设备列表（已分类）')
        .option('--skill-id <id>', DEFAULT_SKILL_ID)
        .option('--verbose')
        .action(async (opts) => {
            await callPetCareClaw([{name: 'get_pet_devices', args: opts}], opts.skillId, opts.verbose);
        });

    // 手动喂食
    program.command('control_feeder')
        .description('远程触发喂食器出粮')
        .option('--device-id <id>', '指定设备ID（可选，默认第一个）')
        .option('--portion <n>', '出粮量（克）', 20)
        .option('--skill-id <id>', DEFAULT_SKILL_ID)
        .option('--verbose')
        .action(async (opts) => {
            const args = {
                deviceId: opts.deviceId,
                portionSize: parseInt(opts.portion) || 20
            };
            await callPetCareClaw([{name: 'control_feeder', args}], opts.skillId, opts.verbose);
        });

    // 宠物环境简报
    program.command('get_pet_brief')
        .description('生成宠物环境简报')
        .option('--skill-id <id>', DEFAULT_SKILL_ID)
        .option('--verbose')
        .action(async (opts) => {
            await callPetCareClaw([{name: 'get_pet_brief', args: opts}], opts.skillId, opts.verbose);
        });

    // 宠物照护全量数据
    program.command('get_pet_care_data')
        .description('获取宠物照护全量数据')
        .option('--skill-id <id>', DEFAULT_SKILL_ID)
        .option('--verbose')
        .action(async (opts) => {
            await callPetCareClaw([{name: 'get_pet_care_data', args: opts}], opts.skillId, opts.verbose);
        });
}

// ==================== 启动 ====================
const program = new Command();

program
    .name(PROGRAM_NAME)
    .description('宠物照护技能 - 宠物状态查询/喂食控制/环境简报')
    .version(VERSION)
    .option('--tools <json>', '执行多个工具（JSON 数组）')
    .option('--skill-id <id>', DEFAULT_SKILL_ID)
    .option('--verbose')
    .action(async (opts) => {
        if (!opts.tools) {
            program.help();
            return;
        }

        // 验证JSON格式
        let parsedTools;
        try {
            parsedTools = JSON.parse(opts.tools);
        } catch (jsonError) {
            console.error('错误：tools参数不是有效的JSON格式');
            process.exit(1);
        }

        await callPetCareClaw(parsedTools, opts.skillId, opts.verbose);
    });

registerClawCommands(program);
program.parse();
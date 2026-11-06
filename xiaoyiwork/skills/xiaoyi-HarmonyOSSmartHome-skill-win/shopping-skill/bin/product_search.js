// ==================== product_search 子技能 ====================
// 功能：产品搜索功能（智慧生活商城搜索 API）
import path from 'path';
import {fileURLToPath} from 'url';
import { Command } from 'commander';
import {
    hagSkillServicePostMall,
    saveDataToTxt,
    generateTraceId
} from '../../utils/hag-connect/utils.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const PRODUCT_SEARCH_DIR = path.join(__dirname, '../out_put/product_search');
const PRODUCT_SEARCH_TXT = path.join(PRODUCT_SEARCH_DIR, 'search_results.txt');

// 智慧生活商城搜索 API 路径
const MALL_SEARCH_API = '/smart-life/v4/mall/search';

/**
 * 产品搜索
 * @param {Object} options - 搜索选项
 * @param {string} options.keyWords - 搜索关键词
 * @param {string[]} [options.searchType=[]] - 搜索类型
 * @param {string[]} [options.brandType=[]] - 品牌类型
 * @param {string[]} [options.categoryType=[]] - 分类类型
 * @param {number} [options.pageNo=1] - 页码
 * @param {string} [options.sortByPrice='asc'] - 价格排序（asc/desc）
 * @param {string} [options.searchId=''] - 搜索ID
 * @param {string} [options.osType='android'] - 操作系统类型
 * @param {boolean} [verbose=false] - 是否显示详细日志
 * @returns {Promise<Object>} 搜索结果
 * @throws {Error} 当API调用失败或数据解析出错时抛出异常
 */
export async function productSearch(options, verbose = false) {
    const traceId = generateTraceId();
    process.stderr.write(`[trace-id] ${traceId}\n`);

    // 参数校验
    if (!options || !options.keyWords) {
        throw new Error('搜索关键词不能为空');
    }

    // 构建请求体
    const requestBody = {
        keyWords: options.keyWords,
        searchType: options.searchType || [],
        brandType: options.brandType || [],
        categoryType: options.categoryType || [],
        pageNo: options.pageNo || 1,
        sortByPrice: options.sortByPrice || 'asc',
        searchId: options.searchId || ''
    };

    try {
        // 调用智慧生活商城搜索 API
        const response = await hagSkillServicePostMall(MALL_SEARCH_API, requestBody, verbose);

        // 验证响应数据基本结构
        if (!response) {
            throw new Error('API响应为空对象');
        }

        // 解析响应数据
        let searchResult = {
            products: [],
            hasNext: false,
            pageNo: 1,
            brands: [],
            category: {},
            platforms: [],
            searchCardInfo: null
        };

        if (response.products) {
            searchResult = {
                products: response.products || [],
                hasNext: response.hasNext || false,
                pageNo: response.pageNo || 1,
                brands: response.brands || [],
                category: response.category || {},
                platforms: response.platforms || [],
                searchCardInfo: response.searchCardInfo || null
            };
        }

        // 处理商品列表，提取关键信息
        const productList = searchResult.products.map((product) => ({
            platform: product.platform || '',
            id: product.id || '',
            name: product.name || '',
            brandName: product.brandName || '',
            category1: product.category1 || '',
            category2: product.category2 || '',
            category3: product.category3 || '',
            model: product.model || '',
            introduction: product.introduction || '',
            imageUrl: product.imageUrl || '',
            clickUrl: product.clickUrl || '',
            originPrice: product.originPrice || 0,
            promoPrice: product.promoPrice || 0
        }));

        // 保存结果到文件
        saveDataToTxt(PRODUCT_SEARCH_TXT, productList, '搜索结果');

        return {
            traceId,
            total: productList.length,
            pageNo: searchResult.pageNo,
            hasNext: searchResult.hasNext,
            brands: searchResult.brands,
            platforms: searchResult.platforms,
            products: productList
        };

    } catch (apiError) {
        console.error(`[error] 产品搜索失败: ${apiError.message}`);
        throw apiError;
    }
}

/**
 * 便捷函数：简单搜索
 * @param {string} keyWords - 搜索关键词
 * @param {boolean} [verbose=false] - 是否显示详细日志
 * @returns {Promise<Object>} 搜索结果
 */
export async function searchProducts(keyWords, verbose = false) {
    return productSearch({ keyWords }, verbose);
}

// ==================== 命令行入口 ====================
const program = new Command();

program
    .name('product_search')
    .description('智慧生活商城产品搜索 API')
    .version('1.0.0')
    .requiredOption('--keywords <keywords>', '搜索关键词（必填）')
    .option('--search-type <type>', '搜索类型，多个用逗号分隔')
    .option('--brand-type <brand>', '品牌类型，多个用逗号分隔')
    .option('--category-type <category>', '分类类型，多个用逗号分隔')
    .option('--page-no <no>', '页码', '1')
    .option('--sort-by-price <sort>', '价格排序（asc/desc）', 'asc')
    .option('--verbose', '显示详细日志')
    .action(async (opts) => {
        try {
            const options = {
                keyWords: opts.keywords,
                searchType: opts.searchType ? opts.searchType.split(',') : [],
                brandType: opts.brandType ? opts.brandType.split(',') : [],
                categoryType: opts.categoryType ? opts.categoryType.split(',') : [],
                pageNo: parseInt(opts.pageNo) || 1,
                sortByPrice: opts.sortByPrice || 'asc'
            };
            const result = await productSearch(options, opts.verbose || false);
            console.log(JSON.stringify(result, null, 2));
        } catch (error) {
            console.error('[error]', error.message);
            process.exit(1);
        }
    });

program.parse(process.argv);

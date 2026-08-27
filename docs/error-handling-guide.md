# 错误处理和降级策略指南

本文档定义了AI驱动产品工作流中各个环节的错误处理策略和降级路径，确保系统在各种异常情况下都能提供合理的用户体验。

## 错误分类和处理策略

### Level 1: 数据获取错误

#### 品类分析数据缺失
**错误**: `品类分析报告不存在`
**影响**: 无法生成PRD和UI设计
**处理**: 
```python
if not category_report_exists:
    print("请先运行品类分析: /category-analysis '品类名'")
    return 1
```
**降级路径**: 无 - 必须先完成品类分析

#### PRD文档过期  
**错误**: `PRD文档距离生成时间>90天`
**影响**: 数据可能过时，UI设计基于过时需求
**处理**:
```python  
if (datetime.now() - prd_date).days > 90:
    print("警告: PRD文档可能过时，建议重新生成")
    # 不阻塞，标注数据来源日期继续执行
```
**降级路径**: 标注警告继续执行，在最终文档中标注数据日期

#### Stitch MCP不可用
**错误**: `检测不到Stitch MCP工具`
**影响**: 无法自动生成UI设计稿
**处理**:
```python
if not detect_stitch_mcp():
    print("Stitch MCP不可用，将生成prompts文档供手动使用")
    # 降级为手动prompts输出
```
**降级路径**: 生成详细的prompts文档，提供手动操作指引

#### 网络API调用失败
**错误**: iTunes API或Google Play API无响应
**影响**: 无法获取最新数据
**处理**:
```python
retry_count = 0
max_retries = 3
while retry_count < max_retries:
    try:
        result = call_api()
        break
    except NetworkError as e:
        retry_count += 1
        if retry_count == max_retries:
            print(f"API调用失败，尝试使用缓存数据: {e}")
            result = load_cached_data()
```
**降级路径**: 使用缓存数据，并在报告中标注数据来源日期

### Level 2: AI分析错误

#### 品类样本不足
**错误**: `搜索结果<5个应用`
**影响**: 分析结果可能不够准确
**处理**:
```python
if len(search_results) < 5:
    print("搜索结果较少，关键词可能不够准确，建议:")
    print("1. 调整搜索关键词")
    print("2. 扩大搜索范围")
    # 不阻塞，继续分析但标注数据有限
```
**降级路径**: 继续分析但标注数据有限的警告

#### PRD功能缺失
**错误**: `PRD缺少功能规格章节`  
**影响**: 无法生成完整的UI设计
**处理**:
```python
if '功能规格' not in prd:
    print("PRD格式不符，降级为基础UI框架")
    # 生成通用设计系统
```
**降级路径**: 生成通用UI设计框架，提示用户完善PRD

#### 状态生成失败
**错误**: `某个交互状态prompt生成失败`
**影响**: UI设计规范不完整
**处理**:
```python
failed_states = []
for state in states:
    try:
        generate_state_prompt(state)
    except Exception as e:
        failed_states.append(state)
        print(f"状态{state}生成失败，跳过")

if failed_states:
    print(f"部分状态生成失败: {failed_states}")
    print("已生成可用状态的prompts，失败状态可手动补充")
```
**降级路径**: 生成成功状态的prompts，标注失败状态供手动补充

### Level 3: 生成错误

#### 单屏Stitch调用失败
**错误**: `Stitch API调用失败`
**影响**: 部分UI界面无法自动生成
**处理**:
```python
for screen in screens:
    for attempt in range(2):  # 重试一次
        try:
            call_stitch(screen)
            break
        except Exception as e:
            if attempt == 0:
                print(f"屏幕{screen}生成失败，重试中...")
            else:
                print(f"屏幕{screen}生成失败，跳过")
                # 继续其他屏幕
                log_failure(screen, str(e))
```
**降级路径**: 跳过失败的屏幕，继续生成其他屏幕，提供手动prompts

#### 内存不足
**错误**: `处理大量应用时内存溢出`
**影响**: 无法处理大规模数据
**处理**:
```python
try:
    process_large_dataset(apps)
except MemoryError:
    print("数据量较大，启用分批处理模式")
    batch_process(apps, batch_size=50)
```
**降级路径**: 分批处理，合并结果

## 降级策略矩阵

| 失败类型 | 降级路径 | 用户体验 | 影响范围 |
|---------|---------|---------|---------|
| 品类分析失败 | 手动输入品类信息 | 需要手动操作 | 完全阻塞 |
| PRD生成失败 | 使用标准模板 | 功能可能不精确 | 部分功能 |
| UI推导失败 | 生成通用设计系统 | 设计不够定制化 | 美观性 |
| Stitch MCP全部失败 | 输出prompts文档 | 需要手动操作 | 自动化程度 |
| 部分屏生成失败 | 混合模式(自动+手动) | 部分手动操作 | 单个界面 |
| 网络API失败 | 使用缓存数据 | 数据可能过时 | 数据新鲜度 |
| 样本数量不足 | 标注警告继续分析 | 结果可信度降低 | 分析准确性 |

## 错误日志规范

所有错误应包含以下信息：

### 标准错误格式
```python
import logging
from datetime import datetime

def log_error(context, error_type, message, details=None, suggestion=None):
    logging.error({
        'timestamp': datetime.now().isoformat(),
        'context': context,          # 哪个环节出错
        'error_type': error_type,    # 错误类型
        'message': message,          # 错误描述
        'details': details or {},     # 详细信息
        'suggestion': suggestion      # 建议解决方案
    })
```

### 错误信息示例
```python
# 数据获取错误
log_error(
    context='category_analysis',
    error_type='api_failure',
    message='iTunes Search API调用失败',
    details={'term': 'pdf scanner', 'status_code': 503},
    suggestion='检查网络连接或使用--refresh重试'
)

# AI分析错误  
log_error(
    context='prd_generation',
    error_type='insufficient_data',
    message='品类样本数量不足',
    details={'sample_count': 3, 'required': 5},
    suggestion='调整搜索关键词或扩大搜索范围'
)

# 生成错误
log_error(
    context='ui_generation',
    error_type='stitch_mcp_unavailable',
    message='Stitch MCP服务不可用',
    details={'mcp_check': False},
    suggestion='将生成prompts文档供手动操作'
)
```

## 性能监控

### 关键环节性能指标
```python
import time
import psutil
import os

def monitor_performance(operation):
    """监控关键操作的性能"""
    start_time = time.time()
    start_memory = psutil.Process(os.getpid()).memory_info().rss
    
    try:
        result = operation()
        duration = time.time() - start_time
        memory_used = (psutil.Process(os.getpid()).memory_info().rss - start_memory) / 1024 / 1024
        
        # 性能警告
        if duration > 30:  # 超过30秒
            print(f"性能提醒: {operation.__name__} 耗时 {duration:.1f}秒")
        
        if memory_used > 500:  # 超过500MB
            print(f"内存提醒: {operation.__name__} 使用 {memory_used:.1f}MB")
        
        return result
        
    except Exception as e:
        print(f"操作失败: {operation.__name__} - {str(e)}")
        raise
```

### 性能基准
- **工具榜扫描**: < 60秒
- **品类分析**: < 90秒  
- **PRD生成**: < 30秒
- **UI设计生成**: < 120秒
- **内存使用**: < 500MB

## 用户友好的错误提示

### 错误提示设计原则
1. **具体明确**: 告诉用户出了什么问题
2. **提供解决方案**: 给出具体的解决建议
3. **保持友好**: 避免技术术语，使用通俗易懂的语言
4. **提供降级路径**: 说明如果不能自动解决，用户可以手动如何处理

### 错误提示模板
```python
ERROR_TEMPLATES = {
    'network_error': """
❌ 网络连接失败
📝 正在尝试: {action}
🔧 建议: 
   1. 检查网络连接
   2. 如果使用代理，确认代理设置正确
   3. 使用 --refresh 重试
    """,
    
    'insufficient_data': """
⚠️  数据样本不足
📊 当前样本: {count} 个，建议: {required}+ 个
🔧 建议:
   1. 调整搜索关键词
   2. 扩大搜索范围  
   3. 选择不同的关键词组合
    """,
    
    'mcp_unavailable': """
🔌 Stitch服务不可用
🤖 自动UI生成已降级为手动模式
📋 将生成详细的prompts文档
🔧 建议: 
   1. 检查Stitch MCP配置
   2. 使用生成的prompts手动操作
   3. 稍后重试自动生成
    """
}
```

## 恢复策略

### 自动恢复
- **网络错误**: 自动重试3次，间隔递增(1s, 2s, 4s)
- **API超时**: 自动重试1次，使用更长超时时间
- **单屏失败**: 跳过当前屏，继续其他屏

### 手动恢复
- **数据缺失**: 提示用户运行前置流程
- **配置错误**: 提供配置检查和修复指引
- **服务不可用**: 提供手动操作文档

### 检查点恢复
```python
def save_checkpoint(operation, data):
    """保存检查点，支持从中断处恢复"""
    checkpoint_file = f".checkpoint_{operation}_{datetime.now().strftime('%Y%m%d')}.json"
    with open(checkpoint_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'data': data,
            'completed_steps': get_completed_steps()
        }, f)

def load_checkpoint(operation):
    """从检查点恢复"""
    checkpoint_file = f".checkpoint_{operation}_*.json"
    if os.path.exists(checkpoint_file):
        with open(checkpoint_file) as f:
            return json.load(f)
    return None
```

## 错误预防

### 输入验证
```python
def validate_input(user_input, input_type):
    """预防性输入验证"""
    validators = {
        'category_slug': validate_slug,
        'platform': validate_platform, 
        'business_model': validate_business_model
    }
    
    if input_type in validators:
        if not validators[input_type](user_input):
            raise ValueError(f"无效的{input_type}: {user_input}")
    return True
```

### 资源检查
```python
def check_resources():
    """执行前资源检查"""
    # 磁盘空间
    disk_usage = psutil.disk_usage('.').percent
    if disk_usage > 90:
        print("警告: 磁盘空间不足")
    
    # 内存可用性
    available_memory = psutil.virtual_memory().available / 1024 / 1024
    if available_memory < 200:
        print("警告: 可用内存不足200MB")
    
    # 网络连接
    if not check_network():
        print("警告: 网络连接异常")
```

通过这些完善的错误处理和降级策略，系统能够在各种异常情况下保持稳定运行，并为用户提供清晰的指引和备选方案。
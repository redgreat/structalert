# 本地调试Docker镜像启动脚本
# 功能：停止旧容器 -> 清理本地日志 -> 删除旧镜像 -> 构建新镜像 -> 启动新容器

# 设置控制台编码为UTF-8
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 项目根目录
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

Write-Host "========================================" -ForegroundColor Green
Write-Host "本地调试Docker镜像启动脚本" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

# 1. 停止并删除旧容器
Write-Host ""
Write-Host "[1/5] 停止并删除旧容器..." -ForegroundColor Yellow
$containers = docker-compose -f docker-compose-local.yml ps -q 2>$null
if ($containers) {
    docker-compose -f docker-compose-local.yml down
    Write-Host "√ 旧容器已停止并删除" -ForegroundColor Green
}
else {
    Write-Host "! 没有运行中的容器" -ForegroundColor Yellow
}

# 2. 清理本地日志文件夹
Write-Host ""
Write-Host "[2/5] 清理本地日志文件夹..." -ForegroundColor Yellow
$LogsDir = Join-Path $ProjectRoot "logs"
if (Test-Path $LogsDir) {
    # 仅删除日志文件保留 logs 目录本身
    Remove-Item -Path "$LogsDir\*" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "√ 本地相关日志已清理" -ForegroundColor Green
}
else {
    Write-Host "! 无日志需要清理" -ForegroundColor Yellow
}

# 3. 删除旧镜像
Write-Host ""
Write-Host "[3/5] 删除旧镜像..." -ForegroundColor Yellow
$imageExists = docker images structalert:local --format "{{.ID}}" 2>$null
if ($imageExists) {
    docker rmi -f structalert:local
    Write-Host "√ 旧镜像已删除" -ForegroundColor Green
}
else {
    Write-Host "! 没有找到旧镜像" -ForegroundColor Yellow
}

# 4. 构建新镜像
Write-Host ""
Write-Host "[4/5] 构建新镜像..." -ForegroundColor Yellow
docker-compose -f docker-compose-local.yml build
# 取消缓存机制构建
# docker-compose -f docker-compose-local.yml build --no-cache
if ($LASTEXITCODE -ne 0) {
    Write-Host "× 镜像构建失败！" -ForegroundColor Red
    exit 1
}
Write-Host "√ 新镜像构建完成" -ForegroundColor Green

# 5. 启动新容器
Write-Host ""
Write-Host "[5/5] 启动新容器..." -ForegroundColor Yellow
docker-compose -f docker-compose-local.yml up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "× 容器启动失败！" -ForegroundColor Red
    exit 1
}
Write-Host "√ 容器已启动" -ForegroundColor Green

# 显示容器状态
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "容器状态" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
docker-compose -f docker-compose-local.yml ps

# 显示日志提示
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "启动完成！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "查看日志: docker-compose -f docker-compose-local.yml logs -f"
Write-Host "手动触发: docker-compose -f docker-compose-local.yml exec structalert python -m structalert compare-now --config /opt/structalert/config/config.yml"
Write-Host "停止服务: docker-compose -f docker-compose-local.yml down"

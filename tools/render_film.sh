#!/bin/bash
# 成片批处理：三张静帧 + 一段环绕序列。后台跑，日志 /tmp/scene/batch.log
BL="/Users/yuyixian/Documents/Qoder/2026-09-13-22-26-38/blender_app/Blender.app/Contents/MacOS/Blender"
HERE="$(cd "$(dirname "$0")" && pwd)"
SC="${HERE}/scene_build.py"
# 前置：贴图目录 PHTEX（Poly Haven CC0 的 *_diff/_nor/_rough.jpg）与输出目录 SCENEOUT
# 第一次跑之前要先 python3 make_leaf.py 生成叶片卡片贴图到 SCENEOUT。
export RATIO=4.0 LOOK="High Contrast" EXPO=-3.4 DEV=CPU
LOG=/tmp/scene/batch.log
: > $LOG
say(){ echo "[$(date +%H:%M:%S)] $*" | tee -a $LOG; }

say "① 英雄帧 1920x1080 @112spp"
RX=1920 RY=1080 SPP=112 CAM=hero TAG=final_hero "$BL" --background --factory-startup --python "$SC" 2>&1 | grep -E "RENDER_SEC|Error|!!" | tee -a $LOG

say "② 奶娃特写 1200x1500 @112spp (f/2.2 景深)"
RX=1200 RY=1500 SPP=112 CAM=mascot TAG=final_mascot FSTOP=2.2 "$BL" --background --factory-startup --python "$SC" 2>&1 | grep -E "RENDER_SEC|Error|!!" | tee -a $LOG

say "③ 侧三分之四 1920x1080 @96spp"
RX=1920 RY=1080 SPP=96 CAM=threeq TAG=final_threeq "$BL" --background --factory-startup --python "$SC" 2>&1 | grep -E "RENDER_SEC|Error|!!" | tee -a $LOG

NF=64
say "④ 环绕序列 $NF 帧 960x540 @20spp"
for i in $(seq 0 $((NF-1))); do
  RX=960 RY=540 SPP=20 ORBIT=$i ORBIT_N=$NF TAG=orb "$BL" --background --factory-startup --python "$SC" >/dev/null 2>&1
  [ $((i % 8)) -eq 0 ] && say "   frame $i/$NF"
  [ $((i % 8)) -eq 7 ] && echo "$i" > /tmp/scene/.orb_progress
done
say "④ 序列完成"

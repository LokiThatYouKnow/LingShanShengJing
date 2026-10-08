<template>
  <div class="avatar-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">
          🤖 数字人配置
          <el-tag v-if="isCloudNoGpu" type="warning" size="small" effect="dark" style="vertical-align:middle;margin-left:10px">
            ☁️ 云服务器 · GPU不可用
          </el-tag>
        </h2>
        <p class="page-subtitle">配置AI数字人形象、音色、语速及讲解风格</p>
      </div>
      <el-button type="primary" @click="saveConfig">保存配置</el-button>
    </div>

    <el-row :gutter="20">
      <!-- 左侧：形象类型切换 + 预览 -->
      <el-col :xs="24" :sm="24" :md="8" :lg="8">
        <el-card class="preview-card">
          <template #header>
            <div class="avatar-type-selector">
              <span class="selector-label">选择形象类型</span>
            <span
              v-if="isDigitalHuman(currentAvatarType) && currentDialogueEngine"
              style="margin-left:10px;font-size:12px;color:#409eff;font-weight:600"
            >
              🔧 {{ ENGINE_META[currentDialogueEngine]?.name || currentDialogueEngine }}
            </span>
            </div>
          </template>

          <div class="avatar-type-tabs">
            <button
              v-for="av in avatarTypes"
              :key="av.id"
              class="type-tab"
              :class="{ active: currentAvatarType === av.id }"
              @click="switchAvatarType(av.id)"
            >
              <span class="tab-icon">{{ av.icon }}</span>
              <span class="tab-label">{{ av.label }}</span>
            </button>
          </div>

          <!-- 数字人舞台 -->
          <div class="avatar-preview-stage">
            <div class="preview-bg"></div>

            <!-- Q版 -->
            <div v-if="currentAvatarType === 'chibi'" class="preview-character">
              <AvatarChibi
                :outfit="chibiOutfit"
                :talking="previewing"
                :loading="false"
                :blinking="blinking"
                :subtitle="previewing ? previewText : ''"
              />
            </div>

            <!-- 漫画风（缩小展示完整人物） -->
            <div v-else-if="currentAvatarType === 'live2d'" class="preview-character live2d-wrap">
              <AvatarLive2D
                :outfit="live2dOutfit"
                :talking="previewing"
                :loading="false"
                :blinking="blinking"
                :subtitle="previewing ? previewText : ''"
              />
            </div>

            <!-- 数字人引擎 (Wav2Lip / SadTalker) -->
            <div v-else-if="isDigitalHuman(currentAvatarType)" class="preview-sadtalker">
              <div v-if="sadPhase === 'idle'" class="sadtalker-idle-preview">
                <!-- 优先播放待机视频（所有引擎统一） -->
                <video
                  v-if="currentIdleVideo"
                  :key="currentIdleVideo"
                  ref="idleVideoRef"
                  :src="currentIdleVideo"
                  autoplay
                  muted
                  playsinline
                  loop
                  class="idle-video-preview"
                ></video>
                <!-- 无待机视频时，显示引擎基础照片作为静态待机图 -->
                <img v-else-if="currentEngineBasePhotoUrl"
                     :src="currentEngineBasePhotoUrl"
                     alt="待机照片"
                     class="idle-photo-preview" />
                <div v-else class="sadtalker-placeholder">
                  <div class="placeholder-avatar-icon">🤖</div>
                  <div class="placeholder-hint">{{ currentConfig.avatar_name || '数字人' }}</div>
                  <div class="placeholder-sub">待机视频 / 基础照片加载中...</div>
                </div>
              </div>
              <div v-else-if="sadPhase === 'generating'" class="sadtalker-generating-preview">
                <div class="gen-ring"></div>
                <p>正在生成视频...</p>
                <p v-if="videoGenPhaseText" class="gen-phase-text">{{ videoGenPhaseText }}</p>
                <p v-if="videoGenElapsedTime > 0" class="gen-elapsed-time">已耗时 {{ formatElapsed(videoGenElapsedTime) }}</p>
              </div>
              <div v-else-if="sadPhase === 'speaking' && previewVideoUrl" class="sadtalker-speaking-preview">
                <video
                  :src="previewVideoUrl"
                  autoplay
                  playsinline
                  class="speaking-video-preview"
                  @ended="sadPhase = 'idle'"
                ></video>
              </div>
            </div>

            <!-- 名牌 -->
            <div class="preview-name-tag">
              <span>{{ currentConfig.avatar_name }}</span>
              <span class="preview-role">景区AI导览员</span>
            </div>
          </div>

        </el-card>
      </el-col>

      <!-- 右侧：配置区域（可滚动） -->
      <el-col :xs="24" :sm="24" :md="16" :lg="16" class="config-col">
        <div class="config-scroll-area">

        <!-- ========== 引擎基础形象照片面板 ========== -->
        <el-card v-if="isDigitalHuman(currentAvatarType)" class="base-photos-card">
          <template #header><span>📷 引擎基础形象照片</span></template>
          <div class="base-photos-grid">
            <div v-for="eng in ['wav2lip', 'sadtalker']" :key="eng" class="base-photo-item">
              <div class="base-photo-thumb"
                   :class="{ 'is-uploading': basePhotoUploadingEngine === eng }"
                   @click="triggerBasePhotoUpload(eng)">
                <img v-if="engineBasePhotos[eng]?.exists"
                     :src="engineBasePhotos[eng].url"
                     class="base-photo-img"
                     :alt="ENGINE_META[eng]?.name" />
                <div v-else class="base-photo-placeholder">
                  <el-icon :size="28"><PictureFilled /></el-icon>
                  <span>暂无照片</span>
                </div>
                <div class="base-photo-overlay">
                  <el-icon :size="16"><Edit /></el-icon>
                  <span>点击替换</span>
                </div>
                <div v-if="basePhotoUploadingEngine === eng" class="base-photo-loading">
                  <el-icon class="is-loading" :size="24"><Loading /></el-icon>
                </div>
              </div>
              <span class="base-photo-label">{{ ENGINE_META[eng]?.icon }} {{ ENGINE_META[eng]?.name }}</span>
              <span class="base-photo-hint">{{ ENGINE_PHOTO_HINTS[eng] }}</span>
              <span class="base-photo-size" v-if="engineBasePhotos[eng]?.exists">
                {{ formatFileSize(engineBasePhotos[eng].size_bytes) }}
              </span>
              <span class="base-photo-size" v-else style="color:#c0c4cc">未设置</span>
            </div>
          </div>
          <input type="file" ref="basePhotoInput" accept="image/*" style="display:none"
                 @change="handleBasePhotoUpload" />
        </el-card>

        <!-- ========== 通用配置：音色与语音 + 欢迎语开场白 ========== -->
        <el-card>
          <template #header><span>🎤 音色与语音配置</span></template>
          <el-form :model="currentConfig" label-width="100px" size="default">
            <el-form-item label="数字人名称">
              <el-input v-model="currentConfig.avatar_name" placeholder="例：小青" style="width:100%;max-width:200px" />
            </el-form-item>
            <el-form-item label="TTS语音">
              <el-switch v-model="currentConfig.tts_enabled"
                         active-text="开启" inactive-text="关闭" />
              <span style="margin-left:12px;color:#888;font-size:12px">
                关闭后数字人将不会语音播报，仅文字回复
              </span>
            </el-form-item>
            <el-form-item label="TTS音色">
              <el-select v-model="currentConfig.voice" style="width:100%">
                <el-option-group label="女声">
                  <el-option v-for="v in voiceOptions.filter(o=>o.gender==='female')" :key="v.value" :label="v.label" :value="v.value">
                    <span>{{ v.label }}</span>
                    <span class="voice-desc">{{ v.desc }}</span>
                  </el-option>
                </el-option-group>
                <el-option-group label="男声">
                  <el-option v-for="v in voiceOptions.filter(o=>o.gender==='male')" :key="v.value" :label="v.label" :value="v.value">
                    <span>{{ v.label }}</span>
                    <span class="voice-desc">{{ v.desc }}</span>
                  </el-option>
                </el-option-group>
              </el-select>
            </el-form-item>
            <el-form-item label="语速">
              <el-slider v-model="currentConfig.speed" :min="0.5" :max="2.0" :step="0.1" style="width:100%;max-width:280px" />
              <span class="slider-val">{{ currentConfig.speed }}x</span>
            </el-form-item>
            <el-form-item label="音调">
              <el-slider v-model="currentConfig.pitch" :min="-10" :max="10" :step="1" style="width:100%;max-width:280px" />
              <span class="slider-val">{{ currentConfig.pitch > 0 ? '+' : '' }}{{ currentConfig.pitch }}</span>
            </el-form-item>
            <el-form-item label="音量">
              <el-slider v-model="currentConfig.volume" :min="0" :max="100" style="width:100%;max-width:280px" />
              <span class="slider-val">{{ currentConfig.volume }}%</span>
            </el-form-item>
            <el-form-item label="讲解风格">
              <el-radio-group v-model="currentConfig.style">
                <el-radio value="professional">专业讲解</el-radio>
                <el-radio value="friendly">亲切活泼</el-radio>
                <el-radio value="poetic">文艺诗意</el-radio>
                <el-radio value="historical">历史典故</el-radio>
              </el-radio-group>
            </el-form-item>
          </el-form>

          <!-- 音色试听 -->
          <div style="border-top:1px solid #ebeef5;padding-top:12px;margin-top:12px">
            <div style="display:flex;align-items:center;gap:10px">
              <el-input
                v-model="previewText"
                placeholder="输入文字试听当前音色..."
                style="flex:1"
              />
              <el-button
                type="primary"
                :loading="previewing"
                @click="previewVoice"
              >
                {{ previewing ? '播放中...' : '▶ 试听' }}
              </el-button>
            </div>
          </div>

          <div style="margin-top:12px;text-align:right;border-top:1px solid #ebeef5;padding-top:12px">
            <el-button type="primary" :loading="voiceConfigSaving" @click="saveVoiceConfig">
              💾 保存当前配置
            </el-button>
            <span style="margin-left:8px;color:#888;font-size:12px">仅保存当前形象的音色与语音设置</span>
          </div>
        </el-card>

        <!-- ========== Q版 / 漫画风专属：换装配置 ========== -->
        <el-card v-if="currentAvatarType === 'chibi' || currentAvatarType === 'live2d'" style="margin-top:16px" class="outfit-config-card">
          <template #header>
            <span>{{ currentAvatarType === 'live2d' ? '🌸' : '🎀' }} {{ currentAvatarType === 'live2d' ? '漫画风' : 'Q版' }} 换装配置</span>
          </template>

          <!-- Q版换装选项 -->
          <template v-if="currentAvatarType === 'chibi'">
            <!-- 发型 -->
            <div class="outfit-group">
              <div class="group-label">发型</div>
              <div class="group-options">
                <button
                  v-for="hair in outfitOptions.hairs"
                  :key="hair.id"
                  class="option-chip"
                  :class="{ active: chibiOutfit.hairId === hair.id }"
                  @click="chibiOutfit.hairId = hair.id; chibiOutfit.hairStyle = hair.style; chibiOutfit.hairColor = hair.color"
                >
                  {{ hair.name }}
                </button>
              </div>
            </div>

            <!-- 服装 -->
            <div class="outfit-group">
              <div class="group-label">服装</div>
              <div class="group-options">
                <button
                  v-for="cloth in outfitOptions.clothes"
                  :key="cloth.id"
                  class="option-chip"
                  :class="{ active: chibiOutfit.clothId === cloth.id }"
                  @click="chibiOutfit.clothId = cloth.id; chibiOutfit.outfitBg = cloth.bg; chibiOutfit.accentColor = cloth.accent; chibiOutfit.collarColor = cloth.collar"
                >
                  {{ cloth.name }}
                </button>
              </div>
            </div>

            <!-- 装饰 -->
            <div class="outfit-group">
              <div class="group-label">装饰</div>
              <div class="group-options">
                <button
                  v-for="deco in outfitOptions.decorations"
                  :key="deco.id"
                  class="option-chip deco-chip"
                  :class="{ active: chibiOutfit.decoId === deco.id }"
                  @click="chibiOutfit.decoId = deco.id; chibiOutfit.decoration = deco.emoji"
                >
                  {{ deco.emoji }} {{ deco.name }}
                </button>
              </div>
            </div>
          </template>

          <!-- 漫画风换装选项 -->
          <template v-else-if="currentAvatarType === 'live2d'">
            <!-- 瞳色 -->
            <div class="outfit-group">
              <div class="group-label">瞳色</div>
              <div class="group-options">
                <button
                  v-for="eye in outfitOptions.live2dEyes"
                  :key="eye.id"
                  class="option-chip"
                  :class="{ active: live2dOutfit.irisId === eye.id }"
                  :style="{ background: eye.color, borderColor: live2dOutfit.irisId === eye.id ? '#fff' : 'transparent' }"
                  @click="live2dOutfit.irisId = eye.id; live2dOutfit.irisColor = eye.color"
                >
                  <span v-if="live2dOutfit.irisId === eye.id" style="font-size: 10px;">✓</span>
                </button>
              </div>
            </div>

            <!-- 发型 -->
            <div class="outfit-group">
              <div class="group-label">发型</div>
              <div class="group-options">
                <button
                  v-for="hair in outfitOptions.live2dHairs"
                  :key="hair.id"
                  class="option-chip"
                  :class="{ active: live2dOutfit.hairId === hair.id }"
                  @click="live2dOutfit.hairId = hair.id; live2dOutfit.hairStyle = hair.style; live2dOutfit.hairColor = hair.color"
                >
                  {{ hair.name }}
                </button>
              </div>
            </div>

            <!-- 服装 -->
            <div class="outfit-group">
              <div class="group-label">服装</div>
              <div class="group-options">
                <button
                  v-for="cloth in outfitOptions.live2dClothes"
                  :key="cloth.id"
                  class="option-chip"
                  :class="{ active: live2dOutfit.clothId === cloth.id }"
                  @click="live2dOutfit.clothId = cloth.id; live2dOutfit.clothStyle = cloth.style; live2dOutfit.outfitColor = cloth.color; live2dOutfit.outfitAccent = cloth.accent; live2dOutfit.skirtColor = cloth.skirt"
                >
                  {{ cloth.name }}
                </button>
              </div>
            </div>

            <!-- 装饰 -->
            <div class="outfit-group">
              <div class="group-label">装饰</div>
              <div class="group-options">
                <button
                  v-for="deco in outfitOptions.live2dDecorations"
                  :key="deco.id"
                  class="option-chip deco-chip"
                  :class="{ active: live2dOutfit.decoId === deco.id }"
                  @click="live2dOutfit.decoId = deco.id; live2dOutfit.ornament = deco.emoji"
                >
                  {{ deco.emoji }} {{ deco.name }}
                </button>
              </div>
            </div>

            <!-- 肤色 -->
            <div class="outfit-group">
              <div class="group-label">肤色</div>
              <div class="group-options">
                <button
                  v-for="skin in outfitOptions.live2dSkins"
                  :key="skin.id"
                  class="option-chip"
                  :class="{ active: live2dOutfit.skinId === skin.id }"
                  :style="{ background: skin.color, borderColor: live2dOutfit.skinId === skin.id ? '#fff' : 'transparent' }"
                  @click="live2dOutfit.skinId = skin.id; live2dOutfit.skinColor = skin.color"
                >
                  <span v-if="live2dOutfit.skinId === skin.id" style="font-size: 10px;">✓</span>
                </button>
              </div>
            </div>

            <!-- 袜子 -->
            <div class="outfit-group">
              <div class="group-label">袜子</div>
              <div class="group-options">
                <button
                  v-for="sock in outfitOptions.live2dSocks"
                  :key="sock.id"
                  class="option-chip"
                  :class="{ active: live2dOutfit.sockId === sock.id }"
                  @click="live2dOutfit.sockId = sock.id; live2dOutfit.sockStyle = sock.style; live2dOutfit.sockColor = sock.color"
                >
                  {{ sock.name }}
                </button>
              </div>
            </div>

            <!-- 鞋子 -->
            <div class="outfit-group">
              <div class="group-label">鞋子</div>
              <div class="group-options">
                <button
                  v-for="shoe in outfitOptions.live2dShoes"
                  :key="shoe.id"
                  class="option-chip"
                  :class="{ active: live2dOutfit.shoeId === shoe.id }"
                  @click="live2dOutfit.shoeId = shoe.id; live2dOutfit.shoeStyle = shoe.style; live2dOutfit.shoeColor = shoe.color"
                >
                  {{ shoe.name }}
                </button>
              </div>
            </div>

            <!-- 蝴蝶结 -->
            <div class="outfit-group">
              <div class="group-label">蝴蝶结</div>
              <div class="group-options">
                <button
                  v-for="bow in outfitOptions.live2dBows"
                  :key="bow.id"
                  class="option-chip deco-chip"
                  :class="{ active: live2dOutfit.bowId === bow.id }"
                  @click="live2dOutfit.bowId = bow.id; live2dOutfit.bowStyle = bow.emoji; live2dOutfit.hasBow = true"
                >
                  {{ bow.emoji }}
                </button>
              </div>
            </div>
          </template>
        </el-card>

        <!-- ========== 数字人专属：驱动配置 + 形象变更 ========== -->
        <template v-if="isDigitalHuman(currentAvatarType)">

          <!-- 驱动配置 — 多引擎支持 -->
          <el-card style="margin-top:16px">
            <template #header><span>🎬 数字人引擎配置</span></template>
            <el-form :model="currentConfig" label-width="100px" size="default">

              <!-- 引擎服务开关 -->
              <el-form-item label="引擎开关">
                <div class="engine-switches">
                  <div v-for="eng in ['wav2lip', 'sadtalker']" :key="eng" class="engine-switch-item">
                    <el-switch
                      v-model="engineSwitches[eng]"
                      @change="(val) => toggleEngineSwitch(eng, val)"
                      :loading="engineSwitchLoading[eng]"
                      :disabled="isCloudNoGpu"
                      :active-text="isCloudNoGpu ? '不可用' : (engineSwitches[eng] ? '运行中' : '已停止')"
                    />
                    <span style="margin-left:8px;font-weight:500">
                      {{ ENGINE_META[eng]?.icon || '' }} {{ ENGINE_META[eng]?.name || eng }}
                    </span>
                    <span
                      :style="{marginLeft:'6px',fontSize:'11px',color:isCloudNoGpu ? '#e6a23c' : (engineStatuses[eng]?.ready ? '#67c23a' : '#909399')}"
                    >
                      {{ isCloudNoGpu ? '⚠ GPU不可用' : (engineStatuses[eng]?.ready ? '● 运行中' : '● 已停止') }}
                    </span>
                  </div>
                </div>
                <div v-if="isCloudNoGpu" style="margin-top:6px;color:#e6a23c;font-size:12px">
                  ☁️ 云服务器无 GPU，视频生成功能不可用。对话仅支持文字 + TTS 语音。
                </div>
                <div v-else style="margin-top:6px;color:#888;font-size:12px">
                  关闭不需要的引擎可降低电脑资源占用。关闭后对应引擎的生成功能将不可用。
                </div>
              </el-form-item>

              <!-- 核心引擎选择 -->
              <el-form-item label="核心引擎">
                <el-radio-group v-model="currentConfig.engine" @change="onEngineChange">
                  <el-radio-button
                    v-for="eng in ['wav2lip', 'sadtalker']"
                    :key="eng"
                    :value="eng"
                    :disabled="!engineStatuses[eng]?.ready"
                  >
                    {{ ENGINE_META[eng]?.icon || '' }} {{ ENGINE_META[eng]?.name || eng }}
                    <el-tag v-if="engineStatuses[eng]?.ready" size="small" effect="plain" style="margin-left:4px">在线</el-tag>
                    <el-tag v-else size="small" type="info" effect="plain" style="margin-left:4px">离线</el-tag>
                  </el-radio-button>
                </el-radio-group>
              </el-form-item>

              <!-- 引擎信息卡片 -->
              <el-form-item label="引擎信息">
                <div class="engine-info-box" v-if="currentConfig.engine && ENGINE_META[currentConfig.engine]">
                  <div class="engine-info-row">
                    <span class="engine-info-label">⚡ 实测速度：</span>
                    <span>{{ ENGINE_META[currentConfig.engine].speed }}</span>
                  </div>
                  <div class="engine-info-row">
                    <span class="engine-info-label">🎨 画质评级：</span>
                    <span>{{ ENGINE_META[currentConfig.engine].quality }}</span>
                  </div>
                  <div class="engine-info-row">
                    <span class="engine-info-label">📊 峰值显存：</span>
                    <span>{{ ENGINE_META[currentConfig.engine].gpu.peakVram }}</span>
                    <span style="margin-left:8px;color:#888;font-size:12px">功耗 {{ ENGINE_META[currentConfig.engine].gpu.peakPower }}</span>
                  </div>
                  <div class="engine-info-section">
                    <div class="engine-info-section-title">🖥️ 桌面端</div>
                    <div class="engine-info-row">
                      <span class="engine-info-label">最低：</span>
                      <span>{{ ENGINE_META[currentConfig.engine].gpu.minimum }}</span>
                    </div>
                    <div class="engine-info-row">
                      <span class="engine-info-label">推荐：</span>
                      <span>{{ ENGINE_META[currentConfig.engine].gpu.recommend }}</span>
                    </div>
                  </div>
                  <div class="engine-info-section">
                    <div class="engine-info-section-title">💻 笔记本</div>
                    <div class="engine-info-row">
                      <span class="engine-info-label">最低：</span>
                      <span>{{ ENGINE_META[currentConfig.engine].gpu.laptopMin }}</span>
                    </div>
                    <div class="engine-info-row">
                      <span class="engine-info-label">推荐：</span>
                      <span>{{ ENGINE_META[currentConfig.engine].gpu.laptopRecommend }}</span>
                    </div>
                  </div>
                  <div class="engine-info-row" style="margin-top:8px">
                    <span class="engine-info-label">✅ 优点：</span>
                    <span>{{ ENGINE_META[currentConfig.engine].pros.join('、') }}</span>
                  </div>
                  <div class="engine-info-row">
                    <span class="engine-info-label">⚠️ 缺点：</span>
                    <span>{{ ENGINE_META[currentConfig.engine].cons.join('、') }}</span>
                  </div>
                  <div class="engine-info-desc">{{ ENGINE_META[currentConfig.engine].desc }}</div>
                </div>
              </el-form-item>

              <!-- ===== SadTalker 专属配置 ===== -->
              <template v-if="currentConfig.engine === 'sadtalker'">
                <!-- 云服务器无GPU提示 -->
                <el-alert v-if="isCloudNoGpu" type="warning" :closable="false" show-icon
                  title="云服务器无GPU，视频生成不可用" style="margin-bottom:12px">
                  此服务器运行在纯CPU模式，无法使用 SadTalker/Wav2Lip。对话将仅返回文字 + TTS语音，前端使用CSS动画模拟口型。
                </el-alert>
                <el-form-item label="推理分辨率">
                  <el-select v-model="sadtalkerEngineConfig.resolution" style="width:100%;max-width:240px"
                             :disabled="!currentConfig.sadtalker_enabled || isCloudNoGpu"
                             @change="syncResolutionToEngineConfig">
                    <el-option value="256" label="256×256（推荐 · 低功耗）" />
                    <el-option value="384" label="384×384（均衡）" />
                    <el-option value="512" label="512×512（高清 · ⚠️注意散热）" />
                  </el-select>
                  <div style="margin-top:4px;color:#888;font-size:12px">
                    最低256×256（模型要求），笔记本建议256防过热
                  </div>
                </el-form-item>
                <el-form-item label="服务状态">
                  <el-tag v-if="isCloudNoGpu" type="warning">☁️ 云服务器 · GPU不可用</el-tag>
                  <el-tag v-else :type="sadtalkerStatus.ready ? 'success' : 'danger'">
                    {{ sadtalkerStatus.ready ? 'SadTalker 在线' : '服务离线' }}
                  </el-tag>
                  <span style="margin-left:12px;color:#888;font-size:12px">
                    GPU: {{ isCloudNoGpu ? '不可用（云服务器）' : (sadtalkerStatus.gpu_available ? '可用' : '不可用') }}
                    ({{ sadtalkerStatus.gpu_name || 'N/A' }})
                  </span>
                </el-form-item>
              </template>

              <!-- ===== Wav2Lip 专属配置 ===== -->
              <template v-if="currentConfig.engine === 'wav2lip'">
                <el-alert v-if="isCloudNoGpu" type="warning" :closable="false" show-icon
                  title="云服务器无GPU，视频生成不可用" style="margin-bottom:12px">
                  此服务器运行在纯CPU模式，无法使用视频生成引擎。对话将仅返回文字 + TTS语音。
                </el-alert>
                <el-form-item label="输出分辨率">
                  <el-select v-model="wav2lipEngineConfig.resolution" style="width:100%;max-width:200px" :disabled="isCloudNoGpu">
                    <el-option value="96" label="96×96（极速）" />
                    <el-option value="128" label="128×128（推荐）" />
                    <el-option value="256" label="256×256（均衡）" />
                  </el-select>
                </el-form-item>
                <el-form-item label="面部填充 (px)">
                  <el-slider v-model="wav2lipEngineConfig.padding" :min="0" :max="30" :step="5" show-stops style="width:100%;max-width:200px" :disabled="isCloudNoGpu" />
                  <span style="margin-left:12px;color:#888;font-size:12px">扩大面部区域以减少边缘伪影</span>
                </el-form-item>
                <el-form-item label="服务状态">
                  <el-tag v-if="isCloudNoGpu" type="warning">☁️ 云服务器 · GPU不可用</el-tag>
                  <el-tag v-else :type="engineStatuses.wav2lip?.ready ? 'success' : 'info'">
                    {{ engineStatuses.wav2lip?.ready ? 'Wav2Lip 在线' : (engineStatuses.wav2lip?.model_load_error || '检测中...') }}
                  </el-tag>
                  <span v-if="!isCloudNoGpu && engineStatuses.wav2lip?.gpu_name" style="margin-left:12px;color:#888;font-size:12px">
                    GPU: {{ engineStatuses.wav2lip.gpu_name }}
                  </span>
                </el-form-item>
              </template>

            </el-form>
          </el-card>

          <!-- ========== 视频设置（多引擎） ========== -->
          <el-card style="margin-top:16px" class="opening-video-card">
            <template #header>
              <div style="display:flex;align-items:center;justify-content:space-between">
                <span>🎬 视频设置</span>
                <el-button size="small" @click="refreshOpeningVideoStatus" :loading="openingStatusLoading">🔄 刷新状态</el-button>
              </div>
            </template>

            <el-form :model="openingVideoForm" label-width="120px" size="default">
              <el-form-item label="开场白内容">
                <el-input
                  v-model="openingVideoForm.text"
                  type="textarea"
                  :rows="3"
                  placeholder="请输入开场白文字内容"
                />
              </el-form-item>

              <el-form-item label="TTS音色">
                <span style="color:#888;font-size:13px">
                  💡 使用上方「🎤 音色与语音配置」中当前形象的音色、语速和音调设置
                </span>
              </el-form-item>

              <el-form-item label="选择引擎">
                <el-radio-group v-model="openingVideoForm.engine">
                  <el-radio-button
                    v-for="eng in ['wav2lip', 'sadtalker']"
                    :key="eng"
                    :value="eng"
                    :disabled="!engineStatuses[eng]?.ready"
                  >
                    {{ ENGINE_META[eng]?.icon || '' }} {{ ENGINE_META[eng]?.name || eng }}
                    <el-tag v-if="engineStatuses[eng]?.ready" size="small" effect="plain" style="margin-left:4px">在线</el-tag>
                    <el-tag v-else size="small" type="info" effect="plain" style="margin-left:4px">离线</el-tag>
                  </el-radio-button>
                </el-radio-group>
              </el-form-item>

              <el-form-item>
                <el-button
                  type="primary"
                  :loading="openingVideoGenerating"
                  :disabled="!openingVideoForm.text || !openingVideoForm.engine || allEnginesOffline || isCloudNoGpu"
                  @click="generateOpeningVideo"
                >
                  🎬 生成开场白视频
                </el-button>
                <el-button
                  v-if="openingVideoForm.engine === 'sadtalker'"
                  type="warning"
                  :loading="idleVideoGenerating"
                  :disabled="!engineStatuses.sadtalker?.ready || isCloudNoGpu"
                  style="margin-left:10px"
                  @click="generateIdleVideos"
                >
                  🎞️ 生成待机视频 (×1)
                </el-button>
                <span v-if="isCloudNoGpu" style="margin-left:12px;color:#e6a23c;font-size:12px">
                  ☁️ GPU不可用，无法生成视频。对话仅支持文字 + TTS 语音。
                </span>
                <span v-else-if="openingVideoGenerating || idleVideoGenerating" style="margin-left:12px;color:#e6a23c">
                  正在生成中，请耐心等待（约1~3分钟）...
                </span>
                <span v-else-if="allEnginesOffline" style="margin-left:12px;color:#f56c6c;font-size:12px">
                  ⚠️ 所有引擎均离线，无法生成视频。请先启动至少一个引擎服务。
                </span>
                <span v-else-if="!engineStatuses[openingVideoForm.engine]?.ready" style="margin-left:12px;color:#e6a23c;font-size:12px">
                  ⚠️ 所选引擎离线，点击后将尝试远程生成
                </span>
              </el-form-item>
            </el-form>

            <!-- 各引擎视频状态 -->
            <el-divider content-position="left">📂 各引擎已有视频</el-divider>
            <div class="opening-status-grid">
              <div
                v-for="eng in ['wav2lip', 'sadtalker']"
                :key="eng"
                class="opening-status-item"
              >
                <div class="opening-engine-label">
                  <span :style="{color: engineStatuses[eng]?.ready ? '#67c23a' : '#909399'}">●</span>
                  {{ ENGINE_META[eng]?.icon || '' }} {{ ENGINE_META[eng]?.name || eng }}
                </div>

                <!-- 开场白视频 -->
                <div v-if="openingVideoStatuses[eng]" class="opening-status-info">
                  <template v-if="openingVideoStatuses[eng].exists">
                    <el-tag type="primary" size="small" effect="dark">🎬 开场白</el-tag>
                    <el-tag v-if="!openingVideoStatuses[eng].is_current" type="warning" size="small" effect="plain">⚠️ 旧形象</el-tag>
                    <span style="font-size:11px;color:#888;margin-left:4px">
                      {{ formatFileSize(openingVideoStatuses[eng].size_bytes) }}
                    </span>
                    <el-button
                      size="small"
                      text
                      type="primary"
                      style="margin-left:4px"
                      @click="previewOpeningVideo(eng)"
                    >▶ 预览</el-button>
                  </template>
                  <template v-else>
                    <el-tag type="primary" size="small" effect="plain">🎬 开场白</el-tag>
                    <el-tag type="info" size="small">❌ 未生成</el-tag>
                  </template>
                </div>
                <div v-else style="font-size:11px;color:#ccc">
                  加载中...
                </div>

                <!-- 待机视频（仅 SadTalker） -->
                <div v-if="eng === 'sadtalker'" style="margin-top:4px">
                  <template v-if="allEngineVideos[eng]">
                    <template v-for="(vid, vi) in allEngineVideos[eng].filter(v => v.video_type === 'idle')" :key="vi">
                      <el-tag type="warning" size="small" effect="dark">🎞️ 待机</el-tag>
                      <span style="font-size:11px;color:#888;margin-left:4px">
                        {{ vid.filename }} ({{ formatFileSize(vid.size_bytes) }})
                      </span>
                      <el-button
                        size="small"
                        text
                        type="primary"
                        style="margin-left:4px"
                        @click="previewVideoUrl_local(vid.url)"
                      >▶ 预览</el-button>
                    </template>
                    <template v-if="!allEngineVideos[eng].some(v => v.video_type === 'idle')">
                      <el-tag type="warning" size="small" effect="plain">🎞️ 待机</el-tag>
                      <el-tag type="info" size="small">❌ 未生成</el-tag>
                    </template>
                  </template>
                  <template v-else>
                    <el-tag type="warning" size="small" effect="plain">🎞️ 待机</el-tag>
                    <span style="font-size:11px;color:#ccc">加载中...</span>
                  </template>
                </div>
              </div>
            </div>

            <!-- 视频预览弹窗 -->
            <el-dialog v-model="openingPreviewVisible" title="视频预览" :width="isMobile ? '95vw' : '600px'" destroy-on-close>
              <div v-if="openingPreviewUrl" style="margin-bottom:8px">
                <el-tag v-if="openingPreviewLabel" size="small" style="margin-bottom:4px">{{ openingPreviewLabel }}</el-tag>
              </div>
              <video
                v-if="openingPreviewUrl"
                :src="openingPreviewUrl"
                controls
                autoplay
                style="width:100%;max-height:500px;border-radius:8px;background:#000"
              ></video>
              <div v-else style="text-align:center;padding:40px;color:#888">
                暂无预览视频
              </div>
            </el-dialog>
          </el-card>

          <!-- 形象变更 -->
          <el-card style="margin-top:16px" class="avatar-change-card">
            <template #header><span>🎨 数字人形象变更</span></template>

            <el-steps :active="avatarChangeStep" finish-status="success" class="avatar-steps">
              <el-step title="上传图片" />
              <el-step title="预览确认" />
              <el-step title="生成视频" />
            </el-steps>

            <!-- 步骤0：上传图片 -->
            <div v-if="avatarChangeStep === 0" class="avatar-upload-area">
              <!-- 引擎状态指示灯 -->
              <div class="engine-status-lights">
                <div v-for="eng in ['wav2lip', 'sadtalker']" :key="eng" class="engine-status-light-item">
                  <span class="engine-status-dot" :class="{ online: engineStatuses[eng]?.ready, offline: !engineStatuses[eng]?.ready }">●</span>
                  <span class="engine-status-name">{{ ENGINE_META[eng]?.icon || '' }} {{ ENGINE_META[eng]?.name || eng }}</span>
                  <el-tag :type="engineStatuses[eng]?.ready ? 'success' : 'info'" size="small" effect="plain">
                    {{ engineStatuses[eng]?.ready ? '在线' : '离线' }}
                  </el-tag>
                </div>
              </div>

              <el-radio-group v-model="avatarChangeMode" style="margin-bottom:16px">
                <el-radio value="upload">上传本地图片</el-radio>
                <el-radio value="ai">AI生成图片</el-radio>
              </el-radio-group>

              <!-- 上传模式 -->
              <div v-if="avatarChangeMode === 'upload'">
                <!-- 未上传时显示上传框 -->
                <el-upload
                  v-if="!avatarChangePreview"
                  ref="avatarUploadRef"
                  :auto-upload="false"
                  :limit="1"
                  accept="image/*"
                  :on-change="handleAvatarChangeUpload"
                  :show-file-list="false"
                  drag
                  style="width:100%"
                >
                  <el-icon class="el-icon--upload"><upload-filled /></el-icon>
                  <div class="el-upload__text">拖拽图片到此处，或 <em>点击上传</em></div>
                  <div class="el-upload__tip">支持 PNG/JPG 格式，建议使用正方形正面人像</div>
                </el-upload>

                <!-- 已上传时显示图片 + X 关闭按钮 -->
                <div v-if="avatarChangePreview" class="avatar-preview-img-section">
                  <div class="avatar-preview-wrapper">
                    <el-image :src="avatarChangePreview" fit="contain" class="avatar-preview-img" />
                    <el-button
                      class="avatar-preview-close-btn"
                      type="danger"
                      circle
                      size="small"
                      @click="clearAvatarUpload"
                    >
                      <el-icon><Close /></el-icon>
                    </el-button>
                  </div>
                </div>

                <div class="avatar-gender-select">
                  <span style="margin-right:12px">选择性别：</span>
                  <el-radio-group v-model="avatarChangeGender">
                    <el-radio value="female">女性形象</el-radio>
                    <el-radio value="male">男性形象</el-radio>
                  </el-radio-group>
                </div>

                <el-button
                  type="primary"
                  :disabled="!avatarChangeFile"
                  :loading="avatarChangeUploading"
                  style="margin-top:16px"
                  @click="uploadAvatarForChange()"
                >上传并预览</el-button>
              </div>

              <!-- AI生图模式 -->
              <div v-else-if="avatarChangeMode === 'ai'" class="ai-gen-section">
                <!-- 性别选择 -->
                <div class="ai-gen-gender">
                  <span style="margin-right:12px;font-weight:500">选择性别：</span>
                  <el-radio-group v-model="aiGenGender">
                    <el-radio value="female">女性形象</el-radio>
                    <el-radio value="male">男性形象</el-radio>
                  </el-radio-group>
                </div>

                <!-- 风格选择 -->
                <div class="ai-gen-style">
                  <span style="margin-right:12px;font-weight:500">画面风格：</span>
                  <el-radio-group v-model="aiGenStyle">
                    <el-radio value="realistic">写实摄影</el-radio>
                    <el-radio value="3d">3D卡通</el-radio>
                    <el-radio value="anime">二次元</el-radio>
                  </el-radio-group>
                </div>

                <!-- 示例提示词 -->
                <div class="ai-gen-examples">
                  <span style="margin-right:8px;font-size:12px;color:#888">快速填入：</span>
                  <el-tag
                    v-for="(example, idx) in aiGenExamples"
                    :key="idx"
                    style="cursor:pointer;margin:2px 4px"
                    :type="aiGenPrompt === example ? 'primary' : 'info'"
                    effect="plain"
                    size="small"
                    @click="aiGenPrompt = example"
                  >{{ example.length > 26 ? example.slice(0, 26) + '…' : example }}</el-tag>
                </div>

                <!-- 自定义提示词 -->
                <el-input
                  v-model="aiGenPrompt"
                  type="textarea"
                  :rows="2"
                  placeholder="描述你想要生成的形象，例如：一位年轻的女导游，长发，穿着中式制服，表情自然"
                  style="margin-top:10px"
                />

                <!-- 生成状态提示 -->
                <div v-if="aiGenStatus" style="margin-top:10px">
                  <el-alert
                    :title="aiGenStatus"
                    :type="aiGenStatusType"
                    :closable="false"
                    show-icon
                  />
                </div>

                <!-- 生成按钮 -->
                <el-button
                  type="primary"
                  :loading="aiGenLoading"
                  :disabled="!aiGenPrompt.trim()"
                  style="margin-top:12px;width:100%"
                  @click="generateAiImage"
                >
                  {{ aiGenLoading ? '⏳ AI正在生成中...' : '🎨 开始生成' }}
                </el-button>
                <div style="text-align:center;color:#aaa;font-size:11px;margin-top:6px">
                  使用豆包 Seedream 4.5 模型，云端推理，约需 5-20 秒
                </div>

                <!-- 生成结果预览 -->
                <div v-if="aiGenPreviewUrl" class="ai-gen-preview" style="margin-top:16px">
                  <div style="font-weight:500;margin-bottom:6px;color:#303133">生成结果</div>
                  <img
                    :src="aiGenPreviewUrl"
                    class="ai-gen-preview-img"
                    style="display:block;margin:0 auto;max-width:100%;border-radius:8px;border:2px solid #e0e0e0"
                  />
                  <div style="display:flex;gap:10px;margin-top:10px;justify-content:center">
                    <el-button @click="discardAiImage">放弃，重新生成</el-button>
                    <el-button type="primary" @click="useAiGeneratedImage">使用这张图片 →</el-button>
                  </div>
                </div>
              </div>
            </div>

            <!-- 步骤1：预览确认 -->
            <div v-else-if="avatarChangeStep === 1" class="avatar-confirm-section">
              <h3>预览新形象</h3>
              <el-image :src="avatarChangePreview" fit="contain" class="avatar-confirm-img" />

              <!-- 选择要生成视频的引擎 -->
              <div class="engine-select-for-change" style="margin-top:16px">
                <p style="font-weight:500;margin-bottom:8px;color:#303133">选择要生成视频的引擎：</p>
                <el-checkbox-group v-model="avatarChangeSelectedEngines">
                  <el-checkbox v-for="eng in ['wav2lip', 'sadtalker']" :key="eng"
                               :value="eng"
                               :disabled="!engineStatuses[eng]?.ready">
                    {{ ENGINE_META[eng]?.icon }} {{ ENGINE_META[eng]?.name }}
                    <el-tag v-if="!engineStatuses[eng]?.ready" type="info" size="small" effect="plain">离线</el-tag>
                    <el-tag v-else type="success" size="small" effect="plain">在线</el-tag>
                  </el-checkbox>
                </el-checkbox-group>
                <p style="color:#909399;font-size:12px;margin-top:6px">
                  💡 未选中的引擎将保留当前已有视频，不受影响
                </p>
              </div>

              <p style="color:#888;margin-top:12px">如果形象不满意，可以重新上传</p>
              <div class="avatar-confirm-actions">
                <el-button @click="resetAvatarChange">不满意，重新上传</el-button>
                <el-button type="primary" :loading="avatarChangeConfirming"
                           :disabled="avatarChangeSelectedEngines.length === 0"
                           @click="confirmAvatarChange">
                  {{ avatarChangeSelectedEngines.length > 0 ? `为选中引擎生成视频 (${avatarChangeSelectedEngines.length})` : '请先选择引擎' }}
                </el-button>
              </div>
            </div>

            <!-- 步骤2：生成进度 -->
            <div v-else-if="avatarChangeStep === 2" class="avatar-progress-section">
              <el-progress
                :percentage="avatarChangeProgress"
                :status="avatarChangeProgressStatus"
                :stroke-width="18"
                :duration="30"
                :striped="avatarChangeProgressStatus !== 'exception' && avatarChangeProgressStatus !== 'success'"
                :striped-flow="avatarChangeProgressStatus !== 'exception' && avatarChangeProgressStatus !== 'success'"
                style="margin:20px 0"
              />
              <p style="text-align:center;color:#888;font-size:14px">{{ avatarChangeProgressText }}</p>
              <p v-if="avatarChangeProgressStatus !== 'success' && avatarChangeProgressStatus !== 'exception'" style="text-align:center;color:#aaa;font-size:12px;margin-top:4px">
                视频生成需要较长时间，请耐心等待...
              </p>
              <div v-if="avatarChangeProgressStatus === 'exception'" style="text-align:center;margin-top:16px">
                <el-button @click="resetAvatarChange">返回重试</el-button>
              </div>
            </div>

            <!-- 步骤3：完成 -->
            <div v-else-if="avatarChangeStep === 3" class="avatar-complete-section">
              <el-icon color="#67c23a" style="font-size:64px"><circle-check-filled /></el-icon>
              <h3 style="color:#67c23a">数字人形象变更完成！</h3>
              <p>已生成：开场白视频 + 1个待机视频（循环播放）</p>
              <p style="color:#888;font-size:12px">刷新讲解端页面即可看到新形象</p>
              <el-button type="primary" style="margin-top:16px" @click="resetAvatarChange">继续变更</el-button>
            </div>
          </el-card>

        </template>

        </div><!-- /config-scroll-area -->
      </el-col><!-- /config-col -->
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, onActivated, onDeactivated } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled, CircleCheckFilled, Close, PictureFilled, Edit, Loading } from '@element-plus/icons-vue'
import { adminApi } from '@/api'
import AvatarChibi from '@/components/AvatarChibi.vue'
import AvatarLive2D from '@/components/AvatarLive2D.vue'

// ========== 引擎元数据定义 ==========
// 按难度排序：入门(左) → 进阶(中) → 专业(右)
// 实测数据基于 RTX 4080 Laptop 12GB（满血175W）
const ENGINE_META = {
  wav2lip: {
    name: 'Wav2Lip',
    icon: '🚀',
    difficulty: '入门',
    speed: '1.1× 实时（23秒音频 → 21秒生成）',
    quality: '⭐⭐⭐',
    gpu: {
      peakVram: '4.0 GB',
      peakPower: '120W',
      minimum: 'GTX 1060 6G / GTX 1660 Ti 6G（桌面）',
      recommend: 'RTX 3060 8G（桌面）',
      laptopMin: 'RTX 2060 Laptop 6G',
      laptopRecommend: 'RTX 4060 Laptop 8G',
    },
    pros: ['速度快于实时（1.1×）', '显存仅需 4GB', '部署最简单，依赖最少', '唇形同步精度业界标杆', '功耗仅 120W，温度可控'],
    cons: ['仅 GAN 合成画质', '只替换下半脸唇形区域', '无表情/头部姿态变化', '唇周边缘偶有模糊'],
    desc: '经典 GAN 方案（IIIT Hyderabad），SyncNet 判别器确保唇音同步。门槛最低，默认引擎。'
  },
  sadtalker: {
    name: 'SadTalker',
    icon: '🎬',
    difficulty: '专业',
    speed: '~0.01× 实时（10秒视频 → 2-8分钟）',
    quality: '⭐⭐⭐⭐⭐',
    gpu: {
      peakVram: '8-12 GB（视分辨率）',
      peakPower: '200W+',
      minimum: 'RTX 3060 12G（桌面，勉强可用）',
      recommend: 'RTX 4080 16G / RTX 4090 24G（桌面）',
      laptopMin: '⚠️ 不建议任何笔记本',
      laptopRecommend: '⚠️ 不建议任何笔记本（散热+VRAM双重瓶颈）',
    },
    pros: ['3D 全身头部动作驱动', '3DMM 面部建模精度高', '表情+姿态+头部全维度', '学术方案，论文复现度高'],
    cons: ['速度极慢（扩散迭代采样）', 'GPU 100% 满载', '不支持实时交互', '⚠️ 笔记本极易过热降频/死机', '三阶段流水线依赖复杂'],
    desc: '基于 3DMM 的扩散生成方案。效果全面但计算量巨大，仅推荐高端桌面显卡。笔记本用户请选 Wav2Lip。'
  }
}

// 各引擎基础照片的上传要求提示
const ENGINE_PHOTO_HINTS = {
  wav2lip:   '✅ 正面照 · 嘴唇清晰可见',
  sadtalker: '✅ 正面免冠照 · 光线均匀',
}

// ========== 形象类型 ==========
const currentAvatarType = ref('wav2lip')  // 'chibi' | 'live2d' | 'wav2lip' | 'sadtalker'
const userSwitchedManually = ref(false)   // 用户手动切换过形象类型，避免异步加载覆盖
const avatarTypes = [
  { id: 'chibi',     icon: '🎀', label: 'Q版' },
  { id: 'live2d',   icon: '🌸', label: '漫画风' },
  { id: 'wav2lip',  icon: '🚀', label: 'Wav2Lip' },
  { id: 'sadtalker', icon: '🎬', label: 'SadTalker' },
]

// 判断是否为数字人引擎类型
function isDigitalHuman(type) {
  return ['wav2lip', 'sadtalker'].includes(type)
}

function switchAvatarType(type) {
  console.log('[AvatarView] switchAvatarType 被调用:', type, '当前类型:', currentAvatarType.value)
  try {
    userSwitchedManually.value = true
    currentAvatarType.value = type
    console.log('[AvatarView] currentAvatarType 已更新为:', currentAvatarType.value, 'isDigitalHuman:', isDigitalHuman(type))
    // 切换到数字人引擎时，同步更新 currentDialogueEngine 和 sadtalkerConfig
    if (isDigitalHuman(type)) {
      sadtalkerConfig.value.engine = type
      currentDialogueEngine.value = type
      // 先清空旧引擎的视频，避免短暂显示错误内容
      currentIdleVideo.value = null
      videoCacheBuster.value = Date.now()
      fetchSadTalkerStatus()
      // 确保 UUID 已加载
      if (!currentAvatarUuid.value) {
        adminApi.getCurrentAvatarUuid().then(r => {
          if (r?.avatar_uuid) currentAvatarUuid.value = r.avatar_uuid
        }).catch(() => {})
      }
      fetchIdleVideos()
    } else {
      // 切换到 Q版/漫画风：清空数字人视频状态，停止视频相关请求
      currentIdleVideo.value = null
      previewVideoUrl.value = ''
      sadPhase.value = 'idle'
      console.log('[AvatarView] 已切换到非数字人类型，视频状态已清空')
    }
  } catch (e) {
    console.error('[AvatarView] switchAvatarType 出错:', e)
  }
}

// ========== 引擎基础照片管理 ==========
async function fetchEngineBasePhotos() {
  try {
    const res = await adminApi.getEngineBasePhotos()
    if (res) engineBasePhotos.value = res
  } catch (e) {
    console.error('获取引擎基础照片失败:', e)
  }
}

function triggerBasePhotoUpload(engine) {
  basePhotoUploadingEngine.value = engine
  const input = basePhotoInput.value
  if (!input) {
    basePhotoUploadingEngine.value = null
    return
  }
  input.value = ''
  // 把引擎名存到 DOM 上，handleBasePhotoUpload 从这里读取，避免被 focus 回调清掉
  input.dataset.engine = engine
  // 检测取消：文件对话框关闭后 window regain focus
  const onFocus = () => {
    window.removeEventListener('focus', onFocus)
    // 延迟检查：给 change 事件足够时间触发（500ms 远大于任何正常延迟）
    setTimeout(() => {
      if (!input.files?.length && basePhotoUploadingEngine.value === engine) {
        basePhotoUploadingEngine.value = null
      }
    }, 500)
  }
  window.addEventListener('focus', onFocus)
  input.click()
}

async function handleBasePhotoUpload(event) {
  const file = event.target.files?.[0]
  if (!file) {
    basePhotoUploadingEngine.value = null
    return
  }

  // 从 DOM dataset 读引擎名——不依赖 basePhotoUploadingEngine（可能已被 focus 回调清掉）
  const engine = event.target.dataset.engine
  if (!engine) {
    basePhotoUploadingEngine.value = null
    return
  }
  const formData = new FormData()
  formData.append('engine', engine)
  formData.append('image', file)

  try {
    const res = await adminApi.uploadEngineBasePhoto(formData)
    if (res?.success) {
      ElMessage.success(`${ENGINE_META[engine]?.name || engine} 基础照片已更新`)
      // 后端生成了新 UUID：更新前端缓存 + 刷新视频列表
      if (res.avatar_uuid) {
        currentAvatarUuid.value = res.avatar_uuid
        videoCacheBuster.value = Date.now()
        currentIdleVideo.value = null
      }
      await fetchEngineBasePhotos()
    }
  } catch (e) {
    ElMessage.error('上传失败: ' + (e?.response?.data?.detail || e?.message || '未知错误'))
  } finally {
    basePhotoUploadingEngine.value = null
  }
}

// ========== 预览状态 ==========
const previewing = ref(false)
const blinking = ref(false)
const previewText = ref('')

// SadTalker 预览
const sadPhase = ref('idle')
const previewVideoUrl = ref('')
const currentIdleVideo = ref('')
const videoCacheBuster = ref(Date.now())  // 用于破坏浏览器视频缓存
const idleVideoRef = ref(null)
// 当前对话使用的数字人引擎（左侧面板显示 + 视频生成使用）
const currentDialogueEngine = ref('wav2lip')
// 音色与语音配置卡片的保存按钮 loading 状态
const voiceConfigSaving = ref(false)
// 引擎基础照片状态
const engineBasePhotos = ref({})             // {wav2lip: {exists, url, size_bytes}, sadtalker: {...}}
const basePhotoUploadingEngine = ref(null)   // 当前正在上传照片的引擎（用于 loading 状态）
const basePhotoInput = ref(null)             // 隐藏的 file input ref
// 形象变更引擎选择
const avatarChangeSelectedEngines = ref([])  // 用户在确认步骤选中的引擎列表
// 当前形象 UUID（唯一编号，用于视频文件命名和过滤）
const currentAvatarUuid = ref('')
// 系统能力（无GPU云部署检测）
const systemCapabilities = ref({
  video_generation: true,
  tts: true,
  chat: true,
})
const isCloudNoGpu = computed(() => !systemCapabilities.value.video_generation)

// 各引擎服务状态
const engineStatuses = ref({
  sadtalker: { ready: false, gpu_available: false, gpu_name: '', model_load_error: null },
  wav2lip:  { ready: false, gpu_available: false, gpu_name: '', model_load_error: null },
})
const sadtalkerStatus = computed(() => engineStatuses.value.sadtalker || { ready: false, gpu_available: false, gpu_name: '' })
const generatingVideos = ref(false)
const videoGenPhaseText = ref('')
const videoGenElapsedTime = ref(0)

// ========== 开场白视频设置（多引擎） ==========
const openingVideoForm = ref({
  text: '',  // 默认从 currentConfig 动态获取，避免硬编码
  engine: 'wav2lip'
})
const openingVideoGenerating = ref(false)
const idleVideoGenerating = ref(false)
const openingStatusLoading = ref(false)
const openingVideoStatuses = ref({})
const openingPreviewVisible = ref(false)
const openingPreviewUrl = ref('')
const openingPreviewLabel = ref('')
const allEngineVideos = ref({})  // { sadtalker: [...], wav2lip: [...] } 来自 idle-videos API 的完整列表

// 是否所有引擎都离线
const allEnginesOffline = computed(() => {
  return ['wav2lip', 'sadtalker'].every(eng => !engineStatuses.value[eng]?.ready)
})

// 当前对话引擎的基础照片 URL（用于左侧预览面板 idle 状态显示）
const currentEngineBasePhotoUrl = computed(() => {
  const eng = currentDialogueEngine.value
  return engineBasePhotos.value[eng]?.url || null
})

// ========== 引擎开关（手动启用/禁用各引擎服务） ==========
const engineSwitches = ref({ wav2lip: true, sadtalker: true })
const engineSwitchLoading = ref({ wav2lip: false, sadtalker: false })

async function fetchEngineConfig() {
  try {
    const data = await adminApi.getEngineConfig()
    // 同步后端视频生成能力（无GPU云部署检测）
    if (data?.video_generation_enabled !== undefined) {
      systemCapabilities.value.video_generation = data.video_generation_enabled
    }
    if (data?.engines) {
      for (const eng of ['wav2lip', 'sadtalker']) {
        if (data.engines[eng]) {
          const cfgEnabled = data.engines[eng].enabled
          const isRunning = data.engines[eng].running
          // 引擎开关位置 = 实际运行状态（保持 UI 与真实状态一致）
          engineSwitches.value[eng] = isRunning || cfgEnabled
          // 如果引擎实际在运行但配置中标记为关闭，自动纠正后端配置
          if (isRunning && !cfgEnabled) {
            console.log(`[引擎检测] ${eng} 实际运行中，自动同步配置`)
            adminApi.toggleEngine({ engine: eng, enabled: true }).catch(() => {})
          }
          // 初始化状态对象
          if (!engineStatuses.value[eng]) {
            engineStatuses.value[eng] = { ready: false, gpu_available: false, gpu_name: '', model_loaded: false }
          }
          // 如果端口检测显示进程在运行，但 API 状态尚未更新，先标记为"启动中"
          if (isRunning && !engineStatuses.value[eng]?.ready) {
            engineStatuses.value[eng] = {
              ...engineStatuses.value[eng],
              port_listening: true,
              pid: data.engines[eng].pid
            }
          }
        }
      }
    }
  } catch (e) {
    console.error('获取引擎开关配置失败:', e)
  }
}

async function toggleEngineSwitch(engine, enabled) {
  if (isCloudNoGpu.value) {
    ElMessage.warning('云服务器无GPU，引擎开关不可用')
    engineSwitches.value[engine] = false
    return
  }
  engineSwitchLoading.value[engine] = true
  try {
    await adminApi.toggleEngine({ engine, enabled })
    ElMessage.success(`${ENGINE_META[engine]?.name || engine} ${enabled ? '启动中' : '已关闭'}`)

    // 立即更新状态文字（不等轮询），关闭时直接标为 stopped
    if (!enabled) {
      engineStatuses.value[engine] = { ...engineStatuses.value[engine], ready: false }
    }

    // 轮询等待引擎状态变更（启动最多等 20 秒，关闭等 5 秒）
    const maxWait = enabled ? 20_000 : 5_000
    const start = Date.now()
    while (Date.now() - start < maxWait) {
      await new Promise(r => setTimeout(r, 2000))
      await fetchSadTalkerStatus()
      const ready = engineStatuses.value[engine]?.ready
      if (enabled && ready) {
        ElMessage.success(`${ENGINE_META[engine]?.name || engine} 已启动`)
        break
      }
      if (!enabled && !ready) {
        break
      }
    }
    // 同步配置状态
    if (enabled && !engineStatuses.value[engine]?.ready) {
      ElMessage.warning(`${ENGINE_META[engine]?.name || engine} 启动超时，请检查引擎日志`)
    }
    engineSwitches.value[engine] = enabled
    // 同步 sadtalker_enabled，使下方控件立即可用/禁用
    if (engine === 'sadtalker') {
      sadtalkerConfig.value.sadtalker_enabled = enabled
    }
  } catch (e) {
    console.error('引擎开关切换失败:', e)
    const detail = e?.response?.data?.detail
    ElMessage.error(detail || '引擎开关切换失败')
    // 回滚开关状态（v-model 已先行更新，API 失败需还原）
    engineSwitches.value[engine] = !enabled
    if (engine === 'sadtalker') {
      sadtalkerConfig.value.sadtalker_enabled = !enabled
    }
  } finally {
    engineSwitchLoading.value[engine] = false
  }
}

// 音色映射（前端选项 → Edge-TTS 音色名）
// 微软 zh-CN 女声仅剩 Xiaoxiao、Xiaoyi 两个；男声 Yunyang、Yunxi、Yunjian、Yunxia 四个
const voiceEngineMap = {
  'female_warm': 'zh-CN-XiaoxiaoNeural',
  'female_bright': 'zh-CN-XiaoyiNeural',
  'male_calm': 'zh-CN-YunyangNeural',
  'male_bright': 'zh-CN-YunxiNeural',
}

// ========== 语音选项 ==========
const voiceOptions = [
  { value: 'female_warm', label: '温柔女声（晓晓）', gender: 'female', desc: '温暖亲切，适合景区导览' },
  { value: 'female_bright', label: '明亮女声（晓怡）', gender: 'female', desc: '活泼清晰，适合活动播报' },
  { value: 'male_calm', label: '沉稳男声（云扬）', gender: 'male', desc: '庄重专业，适合历史景区' },
  { value: 'male_bright', label: '活力男声（云希）', gender: 'male', desc: '朝气蓬勃，适合现代景区' }
]

// ========== 三套独立配置 ==========

// Q版配置
const chibiConfig = ref({
  avatar_name: '小Q',
  voice: 'female_warm',
  speed: 1.0,
  pitch: 0,
  volume: 80,
  style: 'friendly',
  tts_enabled: true,
  greeting: '嗨！我是Q版小Q～欢迎来到灵山胜境，有什么可以帮您的吗？',
  default_intro: '灵山胜境是国家5A级景区，位于无锡太湖之滨，拥有灵山大佛、梵宫、九龙灌浴等精彩景点...',
  farewell: '拜拜咯～期待在灵山胜境再次见面！'
})

// 漫画风配置
const live2dConfig = ref({
  avatar_name: '小漫',
  voice: 'female_bright',
  speed: 1.0,
  pitch: 0,
  volume: 80,
  style: 'poetic',
  tts_enabled: true,
  greeting: '欢迎来到灵山胜境～我是小漫，很高兴为您导览，一起探索这片佛国净土吧',
  default_intro: '灵山胜境，位于无锡太湖之滨，是中国最著名的佛教文化主题园区...',
  farewell: '期待与您下次相遇在灵山更美的风景中～'
})

// 数字人配置
const sadtalkerConfig = ref({
  avatar_name: '小灵',
  voice: 'female_warm',
  speed: 1.0,
  pitch: 0,
  volume: 80,
  style: 'professional',
  tts_enabled: true,
  greeting: '您好！欢迎来到灵山胜境，我是AI导览助手小灵，请问有什么可以帮您？',
  default_intro: '灵山胜境是国家5A级景区，位于江苏省无锡市太湖之滨，拥有灵山大佛、灵山梵宫、九龙灌浴、五印坛城等众多精彩景点...',
  farewell: '感谢您的到来，欢迎下次再游灵山胜境！祝您吉祥如意！',
  driver: 'SadTalker',
  sadtalker_enabled: false,
  generation_mode: 'fast',
  engine: 'wav2lip',           // 当前引擎: wav2lip(入门) | sadtalker(专业)
  engine_config: {}              // 引擎专属配置
})

// Wav2Lip 引擎专属配置
const wav2lipEngineConfig = ref({
  resolution: '128',
  padding: 15
})

// SadTalker 引擎专属配置
const sadtalkerEngineConfig = ref({
  resolution: '256'  // 推理分辨率: 256(推荐) | 384 | 512
})

// 当前配置（计算属性 - 响应式返回对象）
const currentConfig = computed(() => {
  if (currentAvatarType.value === 'chibi') return chibiConfig.value
  else if (currentAvatarType.value === 'live2d') return live2dConfig.value
  else return sadtalkerConfig.value  // 所有数字人引擎共用 sadtalkerConfig
})

// 监听类型切换，同步预览文字
watch(currentAvatarType, (type) => {
  if (isDigitalHuman(type)) {
    previewText.value = sadtalkerConfig.value.greeting || ''
  } else {
    const configs = { chibi: chibiConfig, live2d: live2dConfig }
    previewText.value = configs[type]?.value.greeting || ''
  }
}, { immediate: true })

// 监听推理分辨率变化，同步到 engine_config（确保保存时 engine_config 中也是最新值）
watch(() => sadtalkerEngineConfig.value.resolution, (newVal) => {
  if (sadtalkerConfig.value.engine_config && typeof sadtalkerConfig.value.engine_config === 'object') {
    sadtalkerConfig.value.engine_config.resolution = newVal
  }
})

// ========== Q版装扮 ==========
const chibiOutfit = ref({
  hairId: 'h1', clothId: 'c1', decoId: 'd1',
  hairStyle: 'bun', hairColor: '#3d2000',
  outfitBg: 'linear-gradient(180deg, #7dd3fc 0%, #0284c7 100%)',
  accentColor: '#0369a1', collarColor: '#e0f2fe',
  decoration: '🌸',
})

// Q版预览样式
const miniChibiStyle = computed(() => ({
  '--hair-color': chibiOutfit.value.hairColor,
  '--outfit-bg': chibiOutfit.value.outfitBg,
  '--collar-color': chibiOutfit.value.collarColor,
}))

const miniHairStyle = computed(() => {
  const color = chibiOutfit.value.hairColor
  const style = chibiOutfit.value.hairStyle
  let shape = {}
  if (style === 'bun') shape = { borderRadius: '50% 50% 0 0', width: '50px', height: '40px', top: '-5px', left: '10px' }
  else if (style === 'twin') shape = { borderRadius: '40%', width: '70px', height: '60px', top: '0', left: '-5px' }
  else if (style === 'long') shape = { borderRadius: '40% 40% 0 0', width: '60px', height: '80px', top: '5px', left: '5px' }
  else if (style === 'bob') shape = { borderRadius: '40%', width: '55px', height: '50px', top: '0', left: '8px' }
  else if (style === 'short') shape = { borderRadius: '50%', width: '45px', height: '35px', top: '0', left: '12px' }
  else if (style === 'braid') shape = { borderRadius: '40%', width: '60px', height: '70px', top: '0', left: '5px' }
  return { background: color, ...shape }
})

// ========== 漫画风装扮 ==========
const live2dOutfit = ref({
  hairId: 'lh1', hairStyle: 'long-straight', clothId: 'lc1', clothStyle: 'dress',
  decoId: 'ld1', sockId: 'ls1', sockStyle: 'long', shoeId: 'lsh1', shoeStyle: 'mary-jane',
  irisId: 'le1', skinId: 'ls2',
  hairColor: '#7c3aed', irisColor: '#8b5cf6', skinColor: '#ffe0cc',
  outfitColor: '#e879f9', outfitAccent: '#a855f7', skirtColor: '#d946ef',
  ornament: '🌸', hasBow: true, bowId: 'lb1', bowStyle: '🎀',
  bowColorId: 'bc1', bowColor: '#ec4899', sockColor: '#f5f5f5', shoeColor: '#581c87',
})

// ========== 换装选项 ==========
const outfitOptions = {
  hairs: [
    { id: 'h1', name: '丸子头', style: 'bun', color: '#3d2000' },
    { id: 'h2', name: '双马尾', style: 'twin', color: '#8b4513' },
    { id: 'h3', name: '披肩发', style: 'long', color: '#2d1b00' },
    { id: 'h4', name: '波波头', style: 'bob', color: '#d4956a' },
    { id: 'h5', name: '短发', style: 'short', color: '#1a1a1a' },
    { id: 'h6', name: '麻花辫', style: 'braid', color: '#c0793a' },
  ],
  clothes: [
    { id: 'c1', name: '蓝色连衣裙', bg: 'linear-gradient(180deg, #7dd3fc 0%, #0284c7 100%)', accent: '#0369a1', collar: '#e0f2fe' },
    { id: 'c2', name: '粉色JK服', bg: 'linear-gradient(180deg, #fda4af 0%, #e11d48 100%)', accent: '#be123c', collar: '#fff' },
    { id: 'c3', name: '绿色汉服', bg: 'linear-gradient(180deg, #86efac 0%, #16a34a 100%)', accent: '#15803d', collar: '#f0fdf4' },
    { id: 'c4', name: '黄色小洋装', bg: 'linear-gradient(180deg, #fde68a 0%, #d97706 100%)', accent: '#b45309', collar: '#fffbeb' },
    { id: 'c5', name: '紫色洛丽塔', bg: 'linear-gradient(180deg, #c4b5fd 0%, #7c3aed 100%)', accent: '#6d28d9', collar: '#ede9fe' },
    { id: 'c6', name: '橙色运动服', bg: 'linear-gradient(180deg, #fdba74 0%, #ea580c 100%)', accent: '#c2410c', collar: '#fff7ed' },
  ],
  decorations: [
    { id: 'd1', name: '樱花发卡', emoji: '🌸' },
    { id: 'd2', name: '蝴蝶结', emoji: '🎀' },
    { id: 'd3', name: '星星发夹', emoji: '⭐' },
    { id: 'd4', name: '叶子发饰', emoji: '🌿' },
    { id: 'd5', name: '爱心发饰', emoji: '💜' },
    { id: 'd6', name: '水果发夹', emoji: '🍊' },
  ],
  live2dHairs: [
    { id: 'lh1', name: '紫色长直发', style: 'long-straight', color: '#7c3aed' },
    { id: 'lh2', name: '粉色波浪发', style: 'wavy', color: '#ec4899' },
    { id: 'lh3', name: '蓝色短发', style: 'short', color: '#3b82f6' },
    { id: 'lh4', name: '金色卷发', style: 'curly', color: '#eab308' },
    { id: 'lh5', name: '黑色姬发式', style: 'asymmetrical', color: '#1f2937' },
    { id: 'lh6', name: '红色双马尾', style: 'twin-tail', color: '#dc2626' },
    { id: 'lh7', name: '棕色低马尾', style: 'ponytail', color: '#92400e' },
    { id: 'lh8', name: '银灰双辫', style: 'twin-braids', color: '#9ca3af' },
  ],
  live2dClothes: [
    { id: 'lc1', name: '紫色连衣裙', style: 'dress', color: '#e879f9', accent: '#a855f7', skirt: '#d946ef' },
    { id: 'lc2', name: '粉色JK', style: 'jk', color: '#f472b6', accent: '#ec4899', skirt: '#db2777' },
    { id: 'lc3', name: '蓝色护士服', style: 'nurse', color: '#60a5fa', accent: '#3b82f6', skirt: '#2563eb' },
    { id: 'lc4', name: '绿色精灵装', style: 'elf', color: '#4ade80', accent: '#22c55e', skirt: '#16a34a' },
    { id: 'lc6', name: '黑色哥特', style: 'gothic', color: '#6b7280', accent: '#374151', skirt: '#1f2937' },
    { id: 'lc7', name: '橙色运动服', style: 'sports', color: '#fb923c', accent: '#ea580c', skirt: '#fed7aa' },
    { id: 'lc8', name: '青色水手服', style: 'sailor', color: '#22d3ee', accent: '#06b6d4', skirt: '#67e8f9' },
  ],
  live2dDecorations: [
    { id: 'ld1', name: '樱花发饰', emoji: '🌸' },
    { id: 'ld2', name: '蝴蝶结', emoji: '🎀' },
    { id: 'ld3', name: '星星发夹', emoji: '⭐' },
    { id: 'ld4', name: '猫耳', emoji: '🐱' },
    { id: 'ld5', name: '兔耳', emoji: '🐰' },
    { id: 'ld6', name: '爱心发饰', emoji: '💖' },
  ],
  live2dSocks: [
    { id: 'ls1', name: '白色长筒', style: 'long', color: '#f5f5f5' },
    { id: 'ls2', name: '黑色过膝', style: 'knee-high', color: '#1f2937' },
    { id: 'ls3', name: '粉色泡泡', style: 'bubbly', color: '#fda4af' },
    { id: 'ls4', name: '蓝色条纹', style: 'striped', color: '#93c5fd' },
    { id: 'ls5', name: '网格袜', style: 'mesh', color: '#a1a1aa' },
    { id: 'ls6', name: '白色短袜', style: 'short', color: '#ffffff' },
  ],
  live2dShoes: [
    { id: 'lsh1', name: '紫色玛丽珍', style: 'mary-jane', color: '#581c87' },
    { id: 'lsh2', name: '粉色高跟鞋', style: 'heels', color: '#ec4899' },
    { id: 'lsh3', name: '蓝色帆布鞋', style: 'canvas', color: '#3b82f6' },
    { id: 'lsh4', name: '黑色马丁靴', style: 'boots', color: '#1f2937' },
    { id: 'lsh5', name: '白色运动鞋', style: 'sneakers', color: '#f8fafc' },
    { id: 'lsh6', name: '棕色乐福鞋', style: 'loafers', color: '#92400e' },
  ],
  live2dEyes: [
    { id: 'le1', name: '紫色', color: '#8b5cf6' },
    { id: 'le2', name: '蓝色', color: '#3b82f6' },
    { id: 'le3', name: '粉色', color: '#ec4899' },
    { id: 'le4', name: '绿色', color: '#22c55e' },
    { id: 'le5', name: '金色', color: '#eab308' },
    { id: 'le6', name: '红色', color: '#dc2626' },
    { id: 'le7', name: '黑色', color: '#1f2937' },
    { id: 'le8', name: '琥珀', color: '#f59e0b' },
  ],
  live2dSkins: [
    { id: 'ls1', name: '白皙', color: '#fff5ee' },
    { id: 'ls2', name: '自然', color: '#ffe0cc' },
    { id: 'ls3', name: '小麦', color: '#d4a574' },
    { id: 'ls4', name: '古铜', color: '#8d5524' },
    { id: 'ls5', name: '巧克力', color: '#5c3317' },
  ],
  live2dBows: [
    { id: 'lb1', emoji: '🎀' },
    { id: 'lb2', emoji: '🦋' },
    { id: 'lb3', emoji: '🌸' },
    { id: 'lb4', emoji: '⭐' },
    { id: 'lb5', emoji: '💖' },
    { id: 'lb6', emoji: '🌺' },
    { id: 'lb7', emoji: '🍀' },
    { id: 'lb8', emoji: '✨' },
    { id: 'lb9', emoji: '💎' },
    { id: 'lb10', emoji: '🎀' },
    { id: 'lb11', emoji: '🌟' },
    { id: 'lb12', emoji: '❀' },
  ],
}

// ========== 工具函数 ==========
function formatElapsed(seconds) {
  if (seconds < 60) return `${seconds}秒`
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}分${s}秒`
}

// ========== 引擎 → 视频 URL 前缀 ==========
const ENGINE_VIDEO_PREFIX = {
  sadtalker: '/sadtalker-videos',
  wav2lip: '/wav2lip-videos',
}

// ========== 加载待机视频列表（从 Python 后端获取，支持多引擎 + UUID 过滤）==========
async function fetchIdleVideos() {
  try {
    // 使用当前选中的形象类型作为引擎（而非 currentConfig.engine，后者可能被核心引擎单选修改）
    const engine = isDigitalHuman(currentAvatarType.value) ? currentAvatarType.value : (currentConfig.value.engine || 'wav2lip')
    const prefix = ENGINE_VIDEO_PREFIX[engine] || '/wav2lip-videos'
    const uuidParam = currentAvatarUuid.value ? `&avatar_uuid=${currentAvatarUuid.value}` : ''
    const resp = await fetch(`/tts-api/admin/avatar/idle-videos?engine=${engine}${uuidParam}`)
    if (resp.ok) {
      const data = await resp.json()
      // 后端可能返回最新的 avatar_uuid
      if (data.avatar_uuid && !currentAvatarUuid.value) {
        currentAvatarUuid.value = data.avatar_uuid
      }
      const videos = data.videos || []
      if (videos.length > 0) {
        const uuidPrefix = currentAvatarUuid.value
        // 优先：当前 UUID 的待机视频（_idle_）
        const uuidIdleVid = videos.find(v => uuidPrefix && (v.filename || '').startsWith(uuidPrefix + '_idle_'))
        // 其次：当前 UUID 的开场白视频（_opening）
        const uuidOpeningVid = videos.find(v => uuidPrefix && (v.filename || '').startsWith(uuidPrefix + '_opening'))
        // 再次：旧命名的 idle_ 视频
        const oldIdleVid = videos.find(v => (v.filename || '').startsWith('idle_'))
        // 兜底：旧命名的 opening 视频
        const oldOpeningVid = videos.find(v => (v.filename || '').startsWith('opening') && !(v.filename || '').includes('_'))
        // 最后按修改时间排序
        const sortedByTime = [...videos].sort((a, b) => (b.modified || 0) - (a.modified || 0))
        const v = uuidIdleVid || uuidOpeningVid || oldIdleVid || oldOpeningVid || sortedByTime[0]
        const filename = v.filename || v.url.split('/').pop()
        // 始终用当前时间戳作为缓存破坏参数，确保浏览器每次加载最新视频
        currentIdleVideo.value = `${prefix}/${filename}?t=${Date.now()}`
      } else {
        currentIdleVideo.value = null
      }
    }

    // 额外加载所有引擎的完整视频列表（供视频状态网格展示）
    for (const eng of ['wav2lip', 'sadtalker']) {
      try {
        const engResp = await fetch(`/tts-api/admin/avatar/idle-videos?engine=${eng}${uuidParam}`)
        if (engResp.ok) {
          const engData = await engResp.json()
          allEngineVideos.value[eng] = engData.videos || []
        }
      } catch (_) {}
    }
  } catch (e) {
    console.warn('[Admin预览] 获取待机视频失败:', e)
  }
}

// ========== 加载当前数字人形象 ==========
async function fetchCurrentAvatar() {
  try {
    const resp = await fetch('/sadtalker-api/avatar/current')
    if (resp.ok) {
      const data = await resp.json()
      if (data.image_url) {
        // 更新当前形象
        if (isDigitalHuman(currentAvatarType.value)) {
          sadtalkerConfig.value.avatar_image = data.image_path
        }
      }
    }
  } catch (e) {
    console.warn('[Admin预览] 获取当前形象失败:', e)
  }
}

// ========== 预览语音（TTS试听） ==========
let currentAudio = null

// 音色映射（前端ID -> Edge-TTS音色ID）
// 注意：Edge-TTS中文女声只有 Xiaoxiao、Xiaoyi，男声有 Yunxi、Yunjian、Yunyang
const voiceMap = {
  'female_warm': 'zh-CN-XiaoxiaoNeural',   // 晓晓 - 温柔女声
  'female_bright': 'zh-CN-XiaoyiNeural',   // 晓怡 - 明亮女声
  'male_calm': 'zh-CN-YunyangNeural',      // 云扬 - 沉稳男声
  'male_bright': 'zh-CN-YunxiNeural'       // 云希 - 活力男声
}

async function previewVoice() {
  // 停止之前的播放
  if (currentAudio) {
    currentAudio.pause()
    currentAudio = null
  }
  
  const text = previewText.value || currentConfig.value.greeting
  if (!text?.trim()) {
    ElMessage.warning('请先输入试听文字或确认欢迎语不为空')
    previewing.value = false
    return
  }
  
  previewing.value = true
  try {
    const voiceId = voiceMap[currentConfig.value.voice] || 'zh-CN-XiaoxiaoNeural'
    
    // 调用 Python TTS 服务（通过 Vite 代理，/tts-api → /api）
    const resp = await fetch('/tts-api/voice/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text,
        voice: voiceId,
        speed: currentConfig.value.speed,
        pitch: currentConfig.value.pitch,
        volume: currentConfig.value.volume
      })
    })
    
    if (!resp.ok) {
      throw new Error('TTS请求失败: ' + resp.status)
    }
    
    const blob = await resp.blob()
    const url = URL.createObjectURL(blob)
    currentAudio = new Audio(url)
    
    await currentAudio.play()
    
    currentAudio.onended = () => {
      previewing.value = false
      URL.revokeObjectURL(url)
      currentAudio = null
    }
    currentAudio.onerror = (e) => {
      console.error('音频播放错误:', e)
      previewing.value = false
      ElMessage.error('音频播放失败')
      URL.revokeObjectURL(url)
      currentAudio = null
    }
  } catch (e) {
    console.error('TTS预览失败:', e)
    previewing.value = false
    ElMessage.error('TTS服务连接失败: ' + e.message)
  }
}

// ========== 开场白视频设置（多引擎） ==========
async function refreshOpeningVideoStatus() {
  openingStatusLoading.value = true
  try {
    const data = await adminApi.getOpeningVideoStatus()
    openingVideoStatuses.value = data?.engines || {}
  } catch (e) {
    console.error('获取开场白视频状态失败:', e)
  } finally {
    openingStatusLoading.value = false
  }
}

async function generateOpeningVideo() {
  if (!openingVideoForm.value.text || !openingVideoForm.value.engine) {
    ElMessage.warning('请填写开场白内容并选择引擎')
    return
  }
  const eng = openingVideoForm.value.engine
  if (!engineStatuses.value[eng]?.ready) {
    ElMessage.warning(`${ENGINE_META[eng]?.name || eng} 引擎离线，将尝试使用 TTS 生成音频...`)
  }

  openingVideoGenerating.value = true
  try {
    const payload = {
      text: openingVideoForm.value.text,
      voice: voiceEngineMap[currentConfig.value.voice] || 'zh-CN-XiaoxiaoNeural',
      speed: currentConfig.value.speed || 1.0,
      pitch: currentConfig.value.pitch || 0,
      engine: eng,
    }

    const data = await adminApi.generateOpeningVideo(payload)
    ElMessage.success(`✅ ${ENGINE_META[eng]?.name || eng} 开场白视频生成成功！`)
    // 刷新视频设置区状态
    await refreshOpeningVideoStatus()
    // 同时更新左侧预览面板
    videoCacheBuster.value = Date.now()
    currentIdleVideo.value = null
    await fetchIdleVideos()
  } catch (e) {
    console.error('生成开场白视频失败:', e)
    const detail = e?.response?.data?.detail || e?.message
    ElMessage.error('开场白视频生成失败: ' + detail)
  } finally {
    openingVideoGenerating.value = false
  }
}

async function generateIdleVideos() {
  if (!engineStatuses.value.sadtalker?.ready) {
    ElMessage.warning('SadTalker 引擎未在线，无法生成待机视频')
    return
  }
  idleVideoGenerating.value = true
  try {
    ElMessage.info('正在为 SadTalker 生成 1 个待机视频，请耐心等待（约1~3分钟）...')
    const data = await adminApi.generateIdleVideos({ engine: 'sadtalker', count: 1, length: 10 })
    const successCount = data.generated || 0
    if (successCount > 0) {
      ElMessage.success(`✅ 待机视频生成完成！${successCount}/${data.total} 成功`)
      // 刷新待机视频列表 + 左侧预览
      videoCacheBuster.value = Date.now()
      currentIdleVideo.value = null
      await fetchIdleVideos()
    } else {
      ElMessage.error('❌ 待机视频全部生成失败，请检查 SadTalker 服务日志')
    }
  } catch (e) {
    console.error('生成待机视频失败:', e)
    const detail = e?.response?.data?.detail || e?.message
    ElMessage.error('待机视频生成失败: ' + detail)
  } finally {
    idleVideoGenerating.value = false
  }
}

function previewVideoUrl_local(url, label) {
  if (url) {
    openingPreviewUrl.value = url
    openingPreviewLabel.value = label || ''
    openingPreviewVisible.value = true
  } else {
    ElMessage.info('该视频暂不可用')
  }
}

function previewOpeningVideo(engine) {
  const status = openingVideoStatuses.value[engine]
  if (status?.url) {
    previewVideoUrl_local(status.url, `🎬 ${ENGINE_META[engine]?.name || engine} 开场白视频`)
  } else {
    ElMessage.info('该引擎暂无开场白视频')
  }
}

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// ========== SadTalker 生成开场白/待机视频 ==========
async function generateAvatarVideos() {
  generatingVideos.value = true
  sadPhase.value = 'generating'
  videoGenElapsedTime.value = 0

  // 启动计时器，每秒更新
  const timer = setInterval(() => {
    videoGenElapsedTime.value++
  }, 1000)

  try {
    // 1. 先生成开场白视频（预计2~5分钟）
    videoGenPhaseText.value = '正在生成开场白视频...'
    const openingController = new AbortController()
    const openingTimeout = setTimeout(() => openingController.abort(), 15 * 60 * 1000)

    const openingResp = await fetch('/sadtalker-api/generate-opening', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        text: currentConfig.value.greeting || `您好！欢迎来到灵山胜境，我是AI导览助手${currentConfig.value.avatar_name || 'AI助手'}，请问有什么可以帮您？`,
        voice: voiceMap[currentConfig.value.voice] || 'zh-CN-XiaoxiaoNeural',
        session_id: 'greeting_' + Date.now(),
        resolution: sadtalkerEngineConfig.value.resolution || '256'
      }),
      signal: openingController.signal
    })
    clearTimeout(openingTimeout)

    if (openingResp.ok) {
      const openingData = await openingResp.json()
      if (openingData.success) {
        ElMessage.success('开场白视频生成完成')
      }
    } else {
      console.warn('开场白视频生成返回非200:', openingResp.status)
    }

    // 2. 生成1个待机视频
    videoGenPhaseText.value = '正在生成待机视频 1/1...'
    const idleController = new AbortController()
    const idleTimeout = setTimeout(() => idleController.abort(), 15 * 60 * 1000)

    const idleResp = await fetch(`/sadtalker-api/generate-idle?session_id=idle_1_${Date.now()}&length=10&resolution=${sadtalkerEngineConfig.value.resolution || '256'}`, {
      signal: idleController.signal
    })
    clearTimeout(idleTimeout)

    if (!idleResp.ok) {
      console.warn('待机视频生成失败')
    }

    // 3. 刷新待机视频列表
    videoGenPhaseText.value = '正在刷新视频列表...'
    await fetchIdleVideos()

    ElMessage.success('所有视频生成完成！')
  } catch (e) {
    if (e.name === 'AbortError') {
      console.error('视频生成超时(15分钟)')
      ElMessage.error('视频生成超时，请检查 SadTalker 服务状态')
    } else {
      console.error('生成视频失败:', e)
      ElMessage.error('视频生成服务不可用，请检查 SadTalker 服务')
    }
  } finally {
    clearInterval(timer)
    generatingVideos.value = false
    sadPhase.value = 'idle'
    videoGenPhaseText.value = ''
    videoGenElapsedTime.value = 0
  }
}

// ========== 保存当前形象音色配置 ==========
async function saveVoiceConfig() {
  voiceConfigSaving.value = true
  try {
    const cfg = currentConfig.value
    const typeToId = { live2d: 1, chibi: 2, wav2lip: 3, sadtalker: 3 }
    const id = typeToId[currentAvatarType.value] || 3
    // 自动同步 greeting：如果 greeting 使用的是默认模板格式，自动替换为新的 avatar_name
    const name = cfg.avatar_name
    const defaultGreeting = `您好！欢迎来到灵山胜境，我是AI导览助手${name}，请问有什么可以帮您？`
    const isDefaultFormat = /您好！欢迎来到灵山胜境，我是AI导览助手/.test(cfg.greeting || '')
    const greeting = isDefaultFormat ? defaultGreeting : (cfg.greeting || defaultGreeting)
    // 同时更新本地配置，让 UI 立即显示
    cfg.greeting = greeting
    const payload = {
      name: name,
      voice_name: cfg.voice,
      voice_rate: (cfg.speed || 1.0) + 'x',
      voice_pitch: cfg.pitch >= 0 ? '+' + cfg.pitch + 'Hz' : cfg.pitch + 'Hz',
      welcome_text: greeting
    }
    await adminApi.updateAvatar(id, payload)
    ElMessage.success('音色配置已保存')
  } catch (e) {
    console.error('保存音色配置失败:', e)
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    voiceConfigSaving.value = false
  }
}

// ========== 保存配置 ==========
async function saveConfig() {
  // 确定当前生效的引擎：优先用户左侧面板选中的数字人类型，否则取核心引擎单选的值
  const effectiveEngine = isDigitalHuman(currentAvatarType.value)
    ? currentAvatarType.value
    : (sadtalkerConfig.value.engine || 'wav2lip')

  // 数字人类型：对应引擎离线时给出警告，但不阻止保存（引擎配置是偏好设置，不应因引擎离线而丢弃）
  if (isDigitalHuman(currentAvatarType.value)) {
    const engineAvailable = engineStatuses.value[effectiveEngine]?.ready
    if (!engineAvailable) {
      ElMessage.warning('当前形象对应引擎尚未开启，配置已保存，开启引擎后即可使用')
    }
  }

  // 三套形象配置统一保存到 Python 后端（与加载路径一致，共用同一张 avatar_configs 表）。
  // 形象 → 数据库 id 映射：漫画风(live2d)=1，Q版(chibi)=2，数字人(sadtalker)=3。
  // 后端 AvatarUpdate 使用 snake_case 字段，须严格对应，否则 Pydantic 会静默丢弃。
  const toPayload = (cfg, withSadtalker = false) => {
    // 自动同步 greeting：如果 greeting 使用的是默认模板格式，自动替换为新的 avatar_name
    const name = cfg.avatar_name
    const defaultGreeting = `您好！欢迎来到灵山胜境，我是AI导览助手${name}，请问有什么可以帮您？`
    const isDefaultFormat = /您好！欢迎来到灵山胜境，我是AI导览助手/.test(cfg.greeting || '')
    const greeting = isDefaultFormat ? defaultGreeting : (cfg.greeting || defaultGreeting)
    // 同步更新本地配置
    cfg.greeting = greeting
    const p = {
      name: name,
      voice_name: cfg.voice,
      voice_rate: (cfg.speed || 1.0) + 'x',
      voice_pitch: cfg.pitch >= 0 ? '+' + cfg.pitch + 'Hz' : cfg.pitch + 'Hz',
      welcome_text: greeting
    }
    if (withSadtalker) {
      p.sadtalker_enabled = cfg.sadtalker_enabled
      p.generation_mode = cfg.generation_mode || 'fast'
      p.engine = effectiveEngine  // 使用用户当前选中的引擎，而非 cfg.engine（cfg.engine 可能未与左侧面板同步）
      p.engine_config = cfg.engine_config || {}
      p.resolution = sadtalkerEngineConfig.value.resolution  // 推理分辨率 128|256|384|512
    }
    return p
  }
  try {
    // 将当前选中的形象类型和装扮持久化到 engine_config，确保刷新后能恢复
    const mergedEngineConfig = {
      ...(sadtalkerConfig.value.engine_config || {}),
      active_avatar_type: currentAvatarType.value,
      chibiOutfit: { ...chibiOutfit.value },
      live2dOutfit: { ...live2dOutfit.value },
    }
    console.log('[Admin] 保存装扮到 engine_config:', {
      active_avatar_type: currentAvatarType.value,
      chibiOutfitKeys: Object.keys(chibiOutfit.value),
      live2dOutfitKeys: Object.keys(live2dOutfit.value),
      live2dOutfit: live2dOutfit.value,
    })
    sadtalkerConfig.value.engine_config = mergedEngineConfig

    // 基础配置 + 引擎信息（所有形象共享同一个引擎选择）
    const basePayload = toPayload(live2dConfig.value)
    basePayload.engine = effectiveEngine
    basePayload.engine_config = mergedEngineConfig
    await adminApi.updateAvatar(1, basePayload)

    const chibiPayload = toPayload(chibiConfig.value)
    chibiPayload.engine = effectiveEngine
    chibiPayload.engine_config = mergedEngineConfig
    await adminApi.updateAvatar(2, chibiPayload)

    // 同步 sadtalkerConfig.engine = effectiveEngine，确保重新加载时一致性
    sadtalkerConfig.value.engine = effectiveEngine
    await adminApi.updateAvatar(3, toPayload(sadtalkerConfig.value, true))
    ElMessage.success('所有形象配置已保存')

    // 保存成功后：更新对话引擎 + 刷新左侧预览
    if (isDigitalHuman(currentAvatarType.value)) {
      currentDialogueEngine.value = effectiveEngine
      videoCacheBuster.value = Date.now()
      currentIdleVideo.value = null
      await fetchIdleVideos()
      await refreshOpeningVideoStatus()
    }
  } catch (e) {
    console.error('保存配置失败:', e)
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.response?.data?.message || e.message))
  }
}

// ========== 数字人形象变更 ==========
const avatarChangeStep = ref(0)
const avatarChangeMode = ref('upload')
const avatarChangeGender = ref('female')
const avatarChangeFile = ref(null)
const avatarChangePreview = ref('')
const avatarChangeUploading = ref(false)
const avatarChangeConfirming = ref(false)
const avatarChangeProgress = ref(0)
const avatarChangeProgressText = ref('')
const avatarChangeProgressStatus = ref('')
const avatarChangeImagePath = ref('')
const avatarUploadRef = ref(null)

// ========== AI 图像生成 ==========
const aiGenGender = ref('female')
const aiGenStyle = ref('realistic')
const aiGenPrompt = ref('')
const aiGenLoading = ref(false)
const aiGenPreviewUrl = ref('')
const aiGenStatus = ref('')
const aiGenStatusType = ref('info')
const aiGenExamples = [
  '一位年轻的女导游，长发披肩，穿着素雅的白色中式制服，嘴闭合，表情自然亲切',
  '一位阳光的男导游，短发清爽，穿着深蓝色西装，嘴唇闭合，沉稳自信',
  '一位端庄的女讲解员，盘发，身穿汉服风格工作装，闭嘴，优雅大方',
  '一位沉稳的男讲解员，戴着眼镜，穿着灰色中山装，嘴闭合，儒雅专业',
  '一位可爱的女导览员，短发齐耳，穿浅绿色连衣裙，嘴唇闭合，表情文静',
]

function handleAvatarChangeUpload(uploadFile) {
  console.log('[handleAvatarChangeUpload] uploadFile:', uploadFile)
  console.log('[handleAvatarChangeUpload] uploadFile.raw:', uploadFile?.raw)
  avatarChangeFile.value = uploadFile.raw
  const reader = new FileReader()
  reader.onload = (e) => {
    avatarChangePreview.value = e.target.result
    console.log('[handleAvatarChangeUpload] preview set, size:', e.target.result?.length)
  }
  reader.readAsDataURL(uploadFile.raw)
}

function clearAvatarUpload() {
  avatarChangeFile.value = null
  avatarChangePreview.value = ''
  if (avatarUploadRef.value) {
    avatarUploadRef.value.clearFiles()
  }
}

// ========== AI 图像生成逻辑 ==========
async function generateAiImage() {
  if (!aiGenPrompt.value.trim()) {
    ElMessage.warning('请输入形象描述')
    return
  }
  aiGenLoading.value = true
  aiGenStatus.value = ''
  aiGenPreviewUrl.value = ''
  try {
    const genderText = aiGenGender.value === 'female' ? '女性' : '男性'
    const styleMap = { realistic: '写实', '3d': '3D', anime: '二次元' }
    const fullPrompt = `${genderText}导游，${aiGenPrompt.value.trim()}，${styleMap[aiGenStyle.value] || '写实'}风格`

    const data = await adminApi.generateAiImage({
      prompt: fullPrompt,
      resolution: '1024:1024',
      revise: 0,  // 0=禁用 API 内部提示词重写（否则会删掉闭嘴约束）
      gender: aiGenGender.value,  // 以选择的性别为准，覆盖 prompt 中的矛盾描述
    })
    if (data?.data_url) {
      // 后端返回的是完整的 data:image/png;base64,... URL
      aiGenPreviewUrl.value = data.data_url
      aiGenStatus.value = '✅ 图片生成成功！请查看预览，满意后点击"使用这张图片"'
      aiGenStatusType.value = 'success'
    } else {
      throw new Error('AI 未返回图片数据')
    }
  } catch (e) {
    console.error('AI生成图片失败:', e)
    const detail = e?.response?.data?.detail || e?.message || '未知错误'
    aiGenStatus.value = '❌ 生成失败：' + detail
    aiGenStatusType.value = 'error'
  } finally {
    aiGenLoading.value = false
  }
}

function discardAiImage() {
  aiGenPreviewUrl.value = ''
  aiGenStatus.value = ''
}

async function useAiGeneratedImage() {
  if (!aiGenPreviewUrl.value) {
    ElMessage.warning('请先生成图片')
    return
  }
  // data: URL → Blob → File → 上传
  try {
    avatarChangeUploading.value = true
    const resp = await fetch(aiGenPreviewUrl.value)
    const blob = await resp.blob()
    const file = new File([blob], `ai-generated-${Date.now()}.png`, { type: 'image/png' })
    avatarChangeFile.value = file
    avatarChangePreview.value = aiGenPreviewUrl.value
    avatarChangeGender.value = aiGenGender.value

    // 上传到后端（非静默模式，成功后自动进入步骤1）
    await uploadAvatarForChange(false)

    ElMessage.success('AI生成的图片已就绪，确认满意后可开始生成视频')
  } catch (e) {
    console.error('使用AI图片失败:', e)
    ElMessage.error('图片处理失败：' + (e?.message || '未知错误'))
  } finally {
    avatarChangeUploading.value = false
  }
}

async function uploadAvatarForChange(silent = false) {
  if (!avatarChangeFile.value) return
  avatarChangeUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', avatarChangeFile.value)
    formData.append('gender', avatarChangeGender.value)

    const data = await adminApi.uploadAvatarImageForChange(formData)
    console.log('[uploadAvatarForChange] 响应数据:', JSON.stringify(data), '类型:', typeof data)
    if (data && data.success) {
      avatarChangeImagePath.value = data.image_path
      if (data.image_url) {
        avatarChangePreview.value = data.image_url
      }
      if (!silent) {
        avatarChangeStep.value = 1
        ElMessage.success('图片上传成功！请预览确认')
      }
    } else {
      console.error('[uploadAvatarForChange] 响应异常:', data)
      ElMessage.error('上传返回异常数据：' + JSON.stringify(data).slice(0, 200))
    }
  } catch (e) {
    ElMessage.error('上传失败：' + (e.response?.data?.detail || e.message))
  } finally {
    avatarChangeUploading.value = false
  }
}

async function confirmAvatarChange() {
  // 检查用户是否选择了引擎
  if (!avatarChangeSelectedEngines.value || avatarChangeSelectedEngines.value.length === 0) {
    ElMessage.warning('请至少选择一个要生成视频的引擎')
    return
  }

  // 检查所选引擎是否在线
  const offlineSelected = avatarChangeSelectedEngines.value.filter(
    eng => !engineStatuses.value[eng]?.ready
  )
  if (offlineSelected.length === avatarChangeSelectedEngines.value.length) {
    ElMessage.warning('所选引擎均离线，无法生成视频。请先在引擎开关中启动对应服务。')
    return
  }

  if (!avatarChangeImagePath.value) {
    console.warn('[confirmAvatarChange] avatarChangeImagePath 为空，尝试重新上传...')
    if (avatarChangeFile.value) {
      try {
        avatarChangeUploading.value = true
        const formData = new FormData()
        formData.append('file', avatarChangeFile.value)
        formData.append('gender', avatarChangeGender.value)
        const data = await adminApi.uploadAvatarImageForChange(formData)
        if (data.success) {
          avatarChangeImagePath.value = data.image_path
          if (data.image_url) {
            avatarChangePreview.value = data.image_url
          }
        }
      } catch (e) {
        ElMessage.error('图片上传失败：' + (e.response?.data?.detail || e.message))
        return
      } finally {
        avatarChangeUploading.value = false
      }
    }
    if (!avatarChangeImagePath.value) {
      ElMessage.warning('图片尚未上传，请稍候重试')
      return
    }
  }

  // 过滤出实际在线的引擎
  const enginesToProcess = avatarChangeSelectedEngines.value.filter(
    eng => engineStatuses.value[eng]?.ready
  )
  const total = enginesToProcess.length

  avatarChangeConfirming.value = true
  avatarChangeStep.value = 2
  avatarChangeProgress.value = 0
  avatarChangeProgressStatus.value = ''

  const completed = []
  const failed = []
  let sharedUuid = ''  // 第一个引擎生成的 UUID，后续引擎复用

  // 逐个引擎串行处理（避免同时占用 GPU 导致 OOM）
  for (let i = 0; i < enginesToProcess.length; i++) {
    const engine = enginesToProcess[i]
    const engName = ENGINE_META[engine]?.name || engine

    avatarChangeProgressText.value = `正在为 ${engName} 生成开场白视频... (${i + 1}/${total})`
    avatarChangeProgress.value = Math.floor((i / total) * 90)

    const formData = new FormData()
    formData.append('image_path', avatarChangeImagePath.value)
    formData.append('gender', avatarChangeGender.value)
    formData.append('engine', engine)
    // 复用第一个引擎生成的 UUID，确保所有引擎共享同一形象编号
    if (sharedUuid) {
      formData.append('avatar_uuid', sharedUuid)
    }

    try {
      const data = await adminApi.confirmAvatarChange(formData)
      if (data?.success) {
        completed.push(engine)
        if (data?.avatar_uuid) {
          sharedUuid = data.avatar_uuid
          currentAvatarUuid.value = data.avatar_uuid
        }
        avatarChangeProgressText.value = `${engName} ✅ 完成 (${i + 1}/${total})`
      } else {
        failed.push({ engine, error: data?.message || '未知错误' })
        avatarChangeProgressText.value = `${engName} ❌ 失败 (${i + 1}/${total})`
      }
    } catch (e) {
      const errMsg = e?.response?.data?.detail || e?.message || '超时'
      failed.push({ engine, error: errMsg })
      avatarChangeProgressText.value = `${engName} ❌ 失败: ${errMsg} (${i + 1}/${total})`
    }
  }

  avatarChangeProgress.value = 95

  // 汇总结果
  if (completed.length > 0) {
    avatarChangeProgress.value = 100
    avatarChangeProgressStatus.value = 'success'
    const successNames = completed.map(eng => ENGINE_META[eng]?.name || eng).join('、')
    avatarChangeProgressText.value = `✅ 已完成！${successNames} 开场白视频生成成功`
    if (failed.length > 0) {
      const failNames = failed.map(f => `${ENGINE_META[f.engine]?.name || f.engine}: ${f.error}`).join('；')
      avatarChangeProgressText.value += `\n❌ 失败：${failNames}`
    }
  } else {
    avatarChangeProgressStatus.value = 'exception'
    const failNames = failed.map(f => `${ENGINE_META[f.engine]?.name || f.engine}: ${f.error}`).join('；')
    avatarChangeProgressText.value = `❌ 全部失败：${failNames}`
  }

  // 刷新引擎基础照片（confirm 过程保存了 base_photo）
  fetchEngineBasePhotos()

  // 刷新待机视频 & 各引擎开场白视频状态
  videoCacheBuster.value = Date.now()
  currentIdleVideo.value = null
  await Promise.all([fetchIdleVideos(), refreshOpeningVideoStatus()])

  setTimeout(() => {
    avatarChangeStep.value = 3
  }, 1000)

  avatarChangeConfirming.value = false
}

function resetAvatarChange() {
  avatarChangeStep.value = 0
  avatarChangeFile.value = null
  avatarChangePreview.value = ''
  avatarChangeImagePath.value = ''
  avatarChangeProgress.value = 0
  avatarChangeProgressText.value = ''
  avatarChangeProgressStatus.value = ''
  avatarChangeSelectedEngines.value = []
  // 重置 AI 生图状态
  aiGenPreviewUrl.value = ''
  aiGenStatus.value = ''
  aiGenPrompt.value = ''
  if (avatarUploadRef.value) {
    avatarUploadRef.value.clearFiles()
  }
}

// ========== 生命周期 ==========
let blinkTimer = null

onMounted(async () => {
  startBlink()
  // 加载系统能力（检测是否无GPU云部署）
  try {
    const caps = await adminApi.getSystemCapabilities()
    if (caps) systemCapabilities.value = caps
  } catch (e) { /* 保持默认值（有GPU） */ }
  // 加载引擎开关配置 + 引擎状态
  await Promise.all([fetchEngineConfig(), fetchSadTalkerStatus()])

  // 从后端加载已保存的三套数字人配置（Python 后端，共用 avatar_configs 表）。
  try {
    const resp = await adminApi.getAvatarConfig()
    // adminApi 拦截器已 unwrap response.data，直接拿到 { avatars: [...] }
    const avatars = resp?.avatars || []
    const validVoices = new Set(voiceOptions.map(v => v.value))
    const byId = (id) => avatars.find(a => a.id === id) || {}
    // 漫画风 = id=1
    const live2d = byId(1)
    if (live2d.name) live2dConfig.value.avatar_name = live2d.name
    if (live2d.voice_name && validVoices.has(live2d.voice_name)) live2dConfig.value.voice = live2d.voice_name
    if (live2d.welcome_text) live2dConfig.value.greeting = live2d.welcome_text
    // Q版 = id=2
    const chibi = byId(2)
    if (chibi.name) chibiConfig.value.avatar_name = chibi.name
    if (chibi.voice_name && validVoices.has(chibi.voice_name)) chibiConfig.value.voice = chibi.voice_name
    if (chibi.welcome_text) chibiConfig.value.greeting = chibi.welcome_text
    // 数字人 = id=3
    const sadtalker = byId(3)
    if (sadtalker.name) sadtalkerConfig.value.avatar_name = sadtalker.name
    if (sadtalker.voice_name && validVoices.has(sadtalker.voice_name)) sadtalkerConfig.value.voice = sadtalker.voice_name
    if (sadtalker.welcome_text) sadtalkerConfig.value.greeting = sadtalker.welcome_text
    if (sadtalker.sadtalker_enabled !== undefined) sadtalkerConfig.value.sadtalker_enabled = sadtalker.sadtalker_enabled
    if (sadtalker.generation_mode) sadtalkerConfig.value.generation_mode = sadtalker.generation_mode
    if (sadtalker.engine) sadtalkerConfig.value.engine = sadtalker.engine
    if (sadtalker.engine_config && typeof sadtalker.engine_config === 'object') {
      sadtalkerConfig.value.engine_config = sadtalker.engine_config
    }
    // 根据加载的引擎同步专属配置
    const eng = sadtalker.engine || 'wav2lip'
    currentDialogueEngine.value = eng
    // 恢复上次保存的形象类型：
    // 1. 优先从 engine_config.active_avatar_type 读取（支持 chibi/live2d/wav2lip/sadtalker）
    // 2. 否则回退到 engine 字段（仅支持 wav2lip/sadtalker）
    // 但如果用户在加载期间已手动切换，则不覆盖用户选择
    if (!userSwitchedManually.value) {
      const savedType = (sadtalker.engine_config && sadtalker.engine_config.active_avatar_type) || null
      if (savedType && ['chibi', 'live2d', 'wav2lip', 'sadtalker'].includes(savedType)) {
        currentAvatarType.value = savedType
        console.log('[AvatarView] onMounted 从 active_avatar_type 恢复形象类型:', savedType)
      } else if (isDigitalHuman(eng)) {
        currentAvatarType.value = eng
        console.log('[AvatarView] onMounted 从 engine 设置 currentAvatarType =', eng)
      } else {
        console.log('[AvatarView] onMounted 无法确定形象类型，保持默认:', currentAvatarType.value)
      }
    } else {
      console.log('[AvatarView] onMounted 跳过设置 currentAvatarType（用户已手动切换）')
    }
    if (eng === 'wav2lip' && sadtalker.engine_config) {
      if (sadtalker.engine_config.resolution) wav2lipEngineConfig.value.resolution = sadtalker.engine_config.resolution
      if (sadtalker.engine_config.padding !== undefined) wav2lipEngineConfig.value.padding = sadtalker.engine_config.padding
    } else if (eng === 'sadtalker' && sadtalker.engine_config) {
      if (sadtalker.engine_config.resolution) sadtalkerEngineConfig.value.resolution = sadtalker.engine_config.resolution
    }
    // 同时从顶级字段加载分辨率（兼容旧数据）
    if (sadtalker.resolution) sadtalkerEngineConfig.value.resolution = sadtalker.resolution
    // 如果引擎服务离线，强制关闭视频生成
    if (currentConfig.value.engine === 'sadtalker' && !sadtalkerStatus.value.ready) {
      sadtalkerConfig.value.sadtalker_enabled = false
    }
  } catch (e) {
    console.warn('[Admin] 加载数字人配置失败，使用默认值:', e)
  }

  // 初始化开场白视频文本（使用当前配置的 greeting，避免硬编码）
  openingVideoForm.value.text = currentConfig.value.greeting || `您好！欢迎来到灵山胜境，我是AI导览助手${currentConfig.value.avatar_name || 'AI助手'}，请问有什么可以帮您？`

  // 加载待机视频（所有数字人引擎）
  if (isDigitalHuman(currentAvatarType.value)) {
    // 先加载当前形象 UUID，再加载视频
    try {
      const uuidResp = await adminApi.getCurrentAvatarUuid()
      if (uuidResp?.avatar_uuid) {
        currentAvatarUuid.value = uuidResp.avatar_uuid
      }
    } catch (e) { /* ignore */ }
    await Promise.all([
      fetchIdleVideos(),
      fetchEngineBasePhotos(),
      refreshOpeningVideoStatus(),
    ])
    await fetchCurrentAvatar()
  }

  // 加载各引擎开场白视频状态
  refreshOpeningVideoStatus()
})

function startBlink() {
  blinkTimer = setInterval(() => {
    blinking.value = true
    setTimeout(() => { blinking.value = false }, 150)
  }, 3000)
}

onUnmounted(() => {
  clearInterval(blinkTimer)
  // 清理音频
  if (currentAudio) {
    currentAudio.pause()
    currentAudio = null
  }
})

onActivated(async () => {
  startBlink()
  await Promise.all([fetchEngineConfig(), fetchSadTalkerStatus()])
  // 初始化开场白视频文本
  openingVideoForm.value.text = currentConfig.value.greeting || `您好！欢迎来到灵山胜境，我是AI导览助手${currentConfig.value.avatar_name || 'AI助手'}，请问有什么可以帮您？`
  if (isDigitalHuman(currentAvatarType.value)) {
    await Promise.all([
      fetchIdleVideos(),
      fetchEngineBasePhotos(),
      fetchCurrentAvatar(),
    ])
  }
  refreshOpeningVideoStatus()
})

onDeactivated(() => {
  clearInterval(blinkTimer)
})

// ========== 加载所有引擎服务状态 ==========
async function fetchSadTalkerStatus() {
  // 并行查询所有引擎状态
  const engines = [
    { key: 'sadtalker', url: '/sadtalker-api/status' },
    { key: 'wav2lip',  url: '/wav2lip-api/status' },
  ]
  for (const { key, url } of engines) {
    try {
      const resp = await fetch(url)
      if (resp.ok) {
        const data = await resp.json()
        engineStatuses.value[key] = {
          ready: data.ready || false,
          gpu_available: data.gpu_available || false,
          gpu_name: data.gpu_name || '',
          model_loaded: data.model_loaded || false,
          model_load_error: data.model_load_error || null
        }
      }
    } catch (e) {
      engineStatuses.value[key] = { ready: false, gpu_available: false, gpu_name: '', model_loaded: false, model_load_error: '无法连接服务' }
    }
  }
}

// ========== 引擎切换处理 ==========
function onEngineChange(engine) {
  console.log('[Admin] 引擎切换:', engine)
  // 将引擎专属配置同步到 currentConfig.engine_config（保留已有字段如 active_avatar_type）
  if (engine === 'sadtalker') {
    sadtalkerConfig.value.engine_config = {
      ...(sadtalkerConfig.value.engine_config || {}),
      generation_mode: sadtalkerConfig.value.generation_mode || 'fast',
      resolution: sadtalkerEngineConfig.value.resolution
    }
  } else if (engine === 'wav2lip') {
    sadtalkerConfig.value.engine_config = {
      ...(sadtalkerConfig.value.engine_config || {}),
      ...wav2lipEngineConfig.value
    }
  }
  // 切换引擎后重新获取状态和视频列表
  fetchSadTalkerStatus()
  fetchIdleVideos()
}

// ========== 监听分辨率变化，同步到 engine_config ==========
function syncResolutionToEngineConfig() {
  if (sadtalkerConfig.value.engine_config && typeof sadtalkerConfig.value.engine_config === 'object') {
    sadtalkerConfig.value.engine_config.resolution = sadtalkerEngineConfig.value.resolution
  }
}
</script>

<style scoped>
.avatar-page {}
.page-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px; }
.page-title { font-size: 22px; font-weight: 600; }
.page-subtitle { font-size: 13px; color: #888; margin-top: 4px; }

/* 右侧配置区域滚动 */
.config-col {
  max-height: calc(100vh - 100px);
  overflow-y: auto;
  scrollbar-width: thin;
  scrollbar-color: #c0c4cc transparent;
}
.config-col::-webkit-scrollbar {
  width: 6px;
}
.config-col::-webkit-scrollbar-track {
  background: transparent;
}
.config-col::-webkit-scrollbar-thumb {
  background: #c0c4cc;
  border-radius: 3px;
}
.config-col::-webkit-scrollbar-thumb:hover {
  background: #909399;
}
.config-scroll-area {
  padding-bottom: 20px;
}

/* 形象类型切换 */
.avatar-type-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.type-tab {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  border: 2px solid #e4e7ed;
  border-radius: 12px;
  background: #f5f7fa;
  cursor: pointer;
  transition: all 0.2s;
}
.type-tab:hover { border-color: #409eff; background: #ecf5ff; }
.type-tab.active { border-color: #409eff; background: #ecf5ff; color: #409eff; font-weight: 600; }
.tab-icon { font-size: 28px; line-height: 1; }
.tab-label { font-size: 12px; }

/* 预览舞台 */
.preview-card {}
.avatar-preview-stage {
  background: linear-gradient(135deg, #0a1628, #1a3a6a);
  border-radius: 12px;
  height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  margin-bottom: 16px;
}
.preview-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(ellipse at 50% 100%, rgba(64,120,255,0.25), transparent 60%);
}

/* Q版 & 漫画风 */
.preview-character {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  height: 260px;
  width: 100%;
}
.live2d-wrap {
  transform: scale(0.45);
  transform-origin: center bottom;
}

/* SadTalker 预览 */
.preview-sadtalker {
  position: relative;
  z-index: 1;
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.sadtalker-idle-preview,
.sadtalker-generating-preview,
.sadtalker-speaking-preview {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
}
.idle-video-preview,
.speaking-video-preview {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.sadtalker-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}
.placeholder-avatar-icon { font-size: 72px; line-height: 1; filter: drop-shadow(0 0 16px rgba(64,158,255,0.5)); }
.placeholder-sub { color: rgba(255,255,255,0.4); font-size: 12px; }
.placeholder-hint { color: rgba(255,255,255,0.6); font-size: 13px; }
.idle-photo-preview {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  z-index: 2;
  background: #0a1628;
}
.gen-ring {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  border: 4px solid rgba(255,255,255,0.2);
  border-top-color: #409eff;
  animation: spin 1s linear infinite;
  margin-bottom: 12px;
}
@keyframes spin { to { transform: rotate(360deg); } }
.sadtalker-generating-preview p { color: rgba(255,255,255,0.7); font-size: 14px; }
.gen-phase-text { color: rgba(255,255,255,0.9) !important; font-size: 15px !important; margin-top: 8px !important; font-weight: 500; }
.gen-elapsed-time { color: rgba(255,255,255,0.5) !important; font-size: 12px !important; margin-top: 4px !important; font-variant-numeric: tabular-nums; }

/* 名牌 */
.preview-name-tag {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: absolute;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 2;
  background: rgba(0,0,0,0.35);
  padding: 4px 16px;
  border-radius: 20px;
}
.preview-name-tag span:first-child { color: #fff; font-size: 16px; font-weight: 700; }
.preview-role { color: rgba(255,255,255,0.6); font-size: 11px; }

.preview-actions { display: flex; gap: 10px; }
.preview-input { flex: 1; }

.voice-desc { margin-left: 12px; font-size: 12px; color: #aaa; }
.slider-val { margin-left: 12px; font-size: 13px; color: #409eff; font-weight: 600; min-width: 36px; }

/* ========== 换装配置样式 ========== */
.outfit-config-card {}

.outfit-preview-mini {
  display: flex;
  justify-content: center;
  padding: 16px;
  margin-bottom: 16px;
  background: #f5f7fa;
  border-radius: 12px;
}
.live2d-preview {
  transform: scale(0.5);
  transform-origin: center top;
  height: 180px;
  overflow: hidden;
}

/* Q版迷你人物 */
.mini-chibi {
  position: relative;
  width: 100px;
  height: 160px;
}
.mini-hair {
  position: absolute;
  background: var(--hair-color, #3d2000);
  z-index: 1;
}
.mini-hair-deco {
  position: absolute;
  top: -5px;
  right: -5px;
  font-size: 14px;
}
.mini-head {
  position: absolute;
  width: 60px;
  height: 60px;
  background: #ffe0cc;
  border-radius: 50%;
  top: 25px;
  left: 20px;
  z-index: 2;
}
.mini-face {
  position: absolute;
  width: 100%;
  height: 100%;
}
.mini-eye {
  position: absolute;
  width: 8px;
  height: 10px;
  background: #2d1b00;
  border-radius: 50%;
  top: 22px;
}
.mini-eye.left { left: 12px; }
.mini-eye.right { right: 12px; }
.mini-blush {
  position: absolute;
  width: 10px;
  height: 6px;
  background: rgba(255, 150, 150, 0.5);
  border-radius: 50%;
  top: 32px;
}
.mini-blush.left { left: 5px; }
.mini-blush.right { right: 5px; }
.mini-mouth {
  position: absolute;
  width: 8px;
  height: 4px;
  border-bottom: 2px solid #ff9999;
  border-radius: 0 0 50% 50%;
  bottom: 12px;
  left: 50%;
  transform: translateX(-50%);
}
.mini-body {
  position: absolute;
  width: 50px;
  height: 50px;
  background: var(--outfit-bg, linear-gradient(180deg, #7dd3fc 0%, #0284c7 100%));
  border-radius: 10px 10px 0 0;
  top: 80px;
  left: 25px;
  z-index: 1;
}
.mini-collar {
  position: absolute;
  width: 16px;
  height: 8px;
  background: var(--collar-color, #e0f2fe);
  border-radius: 0 0 8px 8px;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
}

/* 换装选项 */
.outfit-group {
  margin-bottom: 16px;
}
.group-label {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 8px;
}
.group-options {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.option-chip {
  padding: 6px 12px;
  border: 1.5px solid #dcdfe6;
  border-radius: 16px;
  background: #fff;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.option-chip:hover { border-color: #409eff; color: #409eff; }
.option-chip.active { border-color: #409eff; background: #ecf5ff; color: #409eff; font-weight: 600; }
.deco-chip { font-size: 14px; }

/* 引擎基础形象照片面板 */
.base-photos-card { margin-bottom: 16px; }
.base-photos-grid {
  display: flex;
  gap: 20px;
  justify-content: center;
  padding: 8px 0;
}
.base-photo-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.base-photo-thumb {
  width: 120px;
  height: 120px;
  border-radius: 12px;
  overflow: hidden;
  border: 2px solid #e4e7ed;
  cursor: pointer;
  position: relative;
  background: #f5f7fa;
  transition: border-color 0.2s, box-shadow 0.2s;
}
.base-photo-thumb:hover {
  border-color: #409eff;
  box-shadow: 0 2px 12px rgba(64, 158, 255, 0.2);
}
.base-photo-thumb.is-uploading {
  pointer-events: none;
  opacity: 0.7;
}
.base-photo-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.base-photo-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #c0c4cc;
  font-size: 12px;
  gap: 4px;
}
.base-photo-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}
.base-photo-thumb:hover .base-photo-overlay {
  opacity: 1;
}
.base-photo-loading {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
}
.base-photo-label {
  font-size: 13px;
  font-weight: 500;
  color: #303133;
}
.base-photo-hint {
  font-size: 11px;
  color: #e6a23c;
  background: #fdf6ec;
  padding: 1px 6px;
  border-radius: 4px;
  line-height: 1.5;
  white-space: nowrap;
}
.base-photo-size {
  font-size: 11px;
  color: #909399;
}

/* 形象变更引擎选择 */
.engine-select-for-change {
  background: #f5f7fa;
  border-radius: 8px;
  padding: 12px 16px;
  margin-top: 12px;
}

/* 数字人形象变更 */
.avatar-change-card { margin-top: 16px; }
.avatar-steps { margin-bottom: 20px; }
.avatar-upload-area { text-align: center; }
.avatar-preview-img-section {
  margin: 16px 0;
}
.avatar-preview-wrapper {
  position: relative;
  display: inline-block;
  max-width: 320px;
  width: 100%;
}
.avatar-preview-img {
  max-width: 320px;
  width: 100%;
  height: auto;
  object-fit: contain;
  border-radius: 8px;
  display: block;
}
.avatar-preview-close-btn {
  position: absolute;
  top: -8px;
  right: -8px;
  z-index: 10;
  box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.avatar-gender-select {
  margin-top: 16px;
  text-align: center;
}
.avatar-confirm-section {
  text-align: center;
  padding: 20px;
}
.avatar-confirm-img {
  max-width: 512px;
  width: 100%;
  height: auto;
  max-height: none;
  object-fit: contain;
  border-radius: 12px;
  margin: 20px auto;
  display: block;
  box-shadow: 0 4px 16px rgba(0,0,0,0.1);
}
.avatar-confirm-actions {
  margin-top: 20px;
  display: flex;
  gap: 12px;
  justify-content: center;
}
.avatar-progress-section {
  padding: 40px 20px;
  text-align: center;
}
.avatar-complete-section {
  text-align: center;
  padding: 40px 20px;
}
.avatar-complete-section h3 { color: #67c23a; margin: 16px 0; }
.avatar-complete-section p { color: #888; font-size: 14px; margin: 8px 0; }

/* AI生图区域 */
.ai-gen-section {
  padding: 8px 0;
}
.ai-gen-gender,
.ai-gen-style {
  margin-bottom: 12px;
  display: flex;
  align-items: center;
}
.ai-gen-examples {
  margin-top: 10px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}
.ai-gen-preview {
  margin-top: 16px;
  overflow: hidden;
  border-radius: 8px;
}
.ai-gen-preview-img {
  width: 100%;
  max-width: 512px;
  height: auto;
  max-height: none;
  object-fit: contain;
  border-radius: 8px;
  border: 2px solid #e0e0e0;
  display: block;
  margin: 0 auto;
}

/* 引擎信息卡片 */
.engine-info-box {
  background: #f5f7fa;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 13px;
  line-height: 1.8;
}
.engine-info-row {
  display: flex;
  align-items: flex-start;
}
.engine-info-label {
  flex-shrink: 0;
  color: #606266;
  font-weight: 500;
  min-width: 110px;
}
.engine-info-section {
  margin-top: 6px;
  padding: 6px 10px;
  background: #fff;
  border-radius: 4px;
  border: 1px solid #ebeef5;
}
.engine-info-section-title {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 2px;
}
.engine-info-desc {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px dashed #dcdfe6;
  color: #909399;
  font-size: 12px;
}

/* ========== 引擎开关 ========== */
.engine-switches {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.engine-switch-item {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}

/* ========== 引擎状态指示灯 ========== */
.engine-status-lights {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.engine-status-light-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #f5f7fa;
  border-radius: 8px;
  border: 1px solid #e4e7ed;
}
.engine-status-dot {
  font-size: 10px;
}
.engine-status-dot.online {
  color: #67c23a;
}
.engine-status-dot.offline {
  color: #c0c4cc;
}
.engine-status-name {
  font-size: 13px;
  font-weight: 500;
}

/* ========== 视频设置 ========== */
.opening-video-card .opening-status-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.opening-video-card .opening-status-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 14px;
  background: #fafafa;
  border-radius: 8px;
  border: 1px solid #ebeef5;
}
.opening-video-card .opening-engine-label {
  font-weight: 600;
  font-size: 14px;
  min-width: 120px;
}
.opening-video-card .opening-status-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* ═══════════════════════════════════════════════════════════
   移动端适配
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
  .avatar-page .page-header { flex-direction: column; align-items: flex-start; gap: 10px; }
  .avatar-page .page-header .el-button { align-self: flex-end; }
  .avatar-type-tabs { gap: 4px; }
  .type-tab { padding: 8px 4px; }
  .tab-icon { font-size: 22px; }
  .tab-label { font-size: 10px; }
  .avatar-preview-stage { height: 240px; }
  .live2d-wrap { transform: scale(0.35); }
  .config-col { max-height: none; overflow-y: visible; }
  .config-scroll-area { padding-bottom: 0; }
  .base-photos-grid { flex-direction: column; align-items: center; gap: 12px; }
  .base-photo-thumb { width: 100px; height: 100px; }
  .outfit-group { margin-bottom: 10px; }
  .group-options { gap: 4px; }
  .option-chip { padding: 4px 8px; font-size: 11px; border-radius: 12px; }
  .avatar-steps { font-size: 12px; }
  .avatar-upload-area { padding: 10px; }
  .avatar-preview-wrapper { max-width: 240px; }
  .avatar-confirm-img { max-width: 100%; }
  .engine-switch-item { flex-wrap: wrap; }
  .engine-status-lights { gap: 8px; }
  .engine-status-light-item { padding: 4px 8px; font-size: 12px; }
  .opening-video-card .opening-status-item { flex-direction: column; align-items: flex-start; gap: 6px; }
}
</style>

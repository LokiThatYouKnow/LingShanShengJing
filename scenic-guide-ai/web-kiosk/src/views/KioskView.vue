<template>
  <div class="kiosk-container" @touchstart="resetIdle" @mousemove="resetIdle" @click="resetIdle">
    <!-- 顶部状态栏 -->
    <header class="kiosk-header">
      <div class="header-left">
        <img src="/logo.svg" alt="景区Logo" class="logo" @error="$event.target.style.display='none'" />
        <div class="scenic-info">
          <h1 class="scenic-name">{{ scenicName }}</h1>
          <span class="current-spot">{{ currentSpot }}</span>
        </div>
      </div>
      <div class="header-center">
        <div class="status-bar">
          <span class="status-dot" :class="{ active: isConnected }"></span>
          <span>{{ isConnected ? (isLoading ? 'AI思考中...' : 'AI导览就绪') : '连接中...' }}</span>
          <span v-if="showAudioHint" class="audio-hint" @click.stop="dismissAudioHint">🔊 没声音？点击一下人物</span>
        </div>
      </div>
      <div class="header-right">
        <!-- 游客登录 & 投诉建议按钮 -->
        <div class="header-actions">
          <button v-if="!touristUser" class="header-action-btn" @click.stop="showTouristLogin = true" title="游客登录">
            👤 登录
          </button>
          <span v-else class="tourist-badge" @click.stop="showTouristProfile = !showTouristProfile">
            {{ touristUser.nickname }}
          </span>
          <!-- 游客快捷操作弹窗 -->
          <transition name="fade">
            <div class="tourist-popup" v-if="showTouristProfile" @click.stop>
              <div class="tourist-popup-item" @click="handleTouristLogout">
                🚪 退出登录
              </div>
            </div>
          </transition>
          <button class="header-action-btn complaint-btn" @click.stop="showComplaintDialog = true" title="投诉与建议">
            📝 投诉/建议
          </button>
        </div>
        <div class="datetime">
          <div class="time">{{ currentTime }}</div>
          <div class="date">{{ currentDate }}</div>
        </div>
        <div class="weather" @click.stop="showWeatherPopup = !showWeatherPopup" title="点击查看详细天气">
          <span class="weather-icon">{{ weather.icon || '☀️' }}</span>
          <span class="temp">{{ weather.temp }}°C</span>
        </div>
      </div>
    </header>

    <!-- 主内容区 -->
    <main class="kiosk-main">

      <!-- ========== 左侧：景点地图/列表面板 ========== -->
      <section class="spot-section" :class="{ expanded: spotPanelVisible }">
        <transition name="slide-from-left">
          <div v-show="spotPanelVisible" class="spot-list-panel">
            <div class="spot-list-header">
              <h3>🏔️ 景点导览</h3>
              <div class="view-toggle">
                <button :class="{ active: spotViewMode === '2d' }" @click="spotViewMode = '2d'">🗺️ 2D地图</button>
                <button :class="{ active: spotViewMode === 'baidu' }" @click="spotViewMode = 'baidu'">🌏 实景地图</button>
                <button :class="{ active: spotViewMode === 'list' }" @click="spotViewMode = 'list'">📋 列表</button>
              </div>
            </div>

            <!-- ===== 2D地图视图 ===== -->
            <div v-if="spotViewMode === '2d'" class="spot-map-container">
              <Scenic2DMap
                :spots="nearbySpots"
                :current-spot="currentSpot"
                @spot-click="selectSpot"
              />
            </div>

            <!-- ===== 百度地图视图 ===== -->
            <div v-else-if="spotViewMode === 'baidu'" class="spot-map-container">
              <BaiduMapView
                :spots="nearbySpots"
                :api-key="baiduMapsAk"
                :center="baiduMapCenter"
                :zoom="15"
                @spot-click="selectSpot"
              />
            </div>

            <!-- ===== 列表视图 ===== -->
            <div v-else class="spot-list-scroll">
              <div
                v-for="spot in nearbySpots"
                :key="spot.id"
                class="spot-list-item"
                :class="{ active: currentSpot === spot.name }"
                @click="selectSpot(spot)"
              >
                <img
                  v-if="spot.image"
                  :src="spot.image"
                  :alt="spot.name"
                  class="spot-list-thumb"
                  @error="$event.target.style.display='none'"
                />
                <span v-else class="spot-list-icon">{{ spot.icon }}</span>
                <div class="spot-list-info">
                  <span class="spot-list-name">{{ spot.name }}</span>
                  <span class="spot-list-desc">{{ spot.description }}</span>
                  <div class="spot-list-meta">
                    <span>🕐 {{ spot.openTime }}</span>
                    <span>💰 {{ spot.price }}</span>
                    <span>📍 {{ spot.distance }}m</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </transition>
      </section>

      <!-- ========== 中间：景区+数字人区 ========== -->
      <section class="avatar-section" :class="{ 'chat-open': chatPanelVisible, 'spot-open': spotPanelVisible }">
        <!-- 景区背景图（可点击移动人物） -->
        <div class="spot-bg" :style="spotBgStyle" @click="onSceneClick">
          <div class="spot-bg-overlay"></div>
          <!-- 路径提示层（可选显示） -->
          <div class="path-hints" v-if="scenePaths.length > 0 && showPathHints">
            <div 
              v-for="(path, idx) in scenePaths" 
              :key="idx"
              class="path-hint"
              :style="{
                left: (path.x - path.width/2) + '%',
                top: (path.y - path.height/2) + '%',
                width: path.width + '%',
                height: path.height + '%'
              }"
            ></div>
          </div>
        </div>

        <!-- 人物切换已移除，默认使用数字人，切换由管理后台控制 -->

        <!-- 换装面板 -->
        <transition name="pop">
          <div class="outfit-panel" v-if="showOutfitPanel" @click.stop>
            <div class="outfit-panel-header">
              <span class="outfit-panel-title">{{ currentAvatarType === 'live2d' ? '漫画风装扮' : '人物装扮' }}</span>
              <button class="outfit-close" @click="showOutfitPanel = false">✕</button>
            </div>

            <!-- Q版角色预览 -->
            <div class="outfit-preview" v-if="currentAvatarType === 'chibi'">
              <div class="preview-char">
                <div class="mini-chibi" :style="miniCharStyle">
                  <div class="mini-hair" :style="currentHairStyle">
                    <span class="mini-hair-deco" v-if="currentOutfit.decoration">{{ currentOutfit.decoration }}</span>
                  </div>
                  <div class="mini-head">
                    <div class="mini-face">
                      <div class="mini-eye left"></div>
                      <div class="mini-eye right"></div>
                      <div class="mini-blush left"></div>
                      <div class="mini-blush right"></div>
                      <div class="mini-mouth"></div>
                    </div>
                  </div>
                  <div class="mini-body" :style="{ background: currentOutfit.outfitBg }">
                    <div class="mini-collar" :style="{ background: currentOutfit.collarColor }"></div>
                  </div>
                  <div class="mini-arm left" :style="{ background: currentOutfit.outfitBg }">
                    <div class="mini-hand"></div>
                  </div>
                  <div class="mini-arm right" :style="{ background: currentOutfit.outfitBg }">
                    <div class="mini-hand"></div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 漫画风角色预览 - 使用真实组件 -->
            <div class="outfit-preview live2d-preview" v-if="currentAvatarType === 'live2d'">
              <AvatarLive2D 
                :outfit="live2dOutfit" 
                :talking="false"
                :loading="false"
                :blinking="true"
              />
            </div>

            <!-- Q版换装选项 -->
            <template v-if="currentAvatarType === 'chibi'">
              <!-- 发型选择 -->
              <div class="outfit-group">
                <div class="group-label">发型</div>
                <div class="group-options">
                  <button
                    v-for="hair in outfitOptions.hairs"
                    :key="hair.id"
                    class="option-chip"
                    :class="{ active: currentOutfit.hairId === hair.id }"
                    @click="applyOutfit({ ...currentOutfit, hairId: hair.id, hairStyle: hair.style, hairColor: hair.color })"
                  >
                    {{ hair.name }}
                  </button>
                </div>
              </div>

              <!-- 服装选择 -->
              <div class="outfit-group">
                <div class="group-label">服装</div>
                <div class="group-options">
                  <button
                    v-for="cloth in outfitOptions.clothes"
                    :key="cloth.id"
                    class="option-chip"
                    :class="{ active: currentOutfit.clothId === cloth.id }"
                    @click="applyOutfit({ ...currentOutfit, clothId: cloth.id, outfitBg: cloth.bg, accentColor: cloth.accent, collarColor: cloth.collar })"
                  >
                    {{ cloth.name }}
                  </button>
                </div>
              </div>

              <!-- 装饰选择 -->
              <div class="outfit-group">
                <div class="group-label">装饰</div>
                <div class="group-options">
                  <button
                    v-for="deco in outfitOptions.decorations"
                    :key="deco.id"
                    class="option-chip deco-chip"
                    :class="{ active: currentOutfit.decoId === deco.id }"
                    @click="applyOutfit({ ...currentOutfit, decoId: deco.id, decoration: deco.emoji })"
                  >
                    {{ deco.emoji }} {{ deco.name }}
                  </button>
                </div>
              </div>
            </template>

            <!-- 漫画风换装选项 -->
            <template v-if="currentAvatarType === 'live2d'">
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
                    @click="applyLive2dOutfit({ ...live2dOutfit, irisId: eye.id, irisColor: eye.color })"
                  >
                    <span v-if="live2dOutfit.irisId === eye.id" style="font-size: 10px;">✓</span>
                  </button>
                </div>
              </div>

              <!-- 装饰选择 -->
              <div class="outfit-group">
                <div class="group-label">装饰</div>
                <div class="group-options">
                  <button
                    v-for="deco in outfitOptions.live2dDecorations"
                    :key="deco.id"
                    class="option-chip deco-chip"
                    :class="{ active: live2dOutfit.decoId === deco.id }"
                    @click="applyLive2dOutfit({ ...live2dOutfit, decoId: deco.id, ornament: deco.emoji })"
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
                    @click="applyLive2dOutfit({ ...live2dOutfit, skinId: skin.id, skinColor: skin.color })"
                  >
                    <span v-if="live2dOutfit.skinId === skin.id" style="font-size: 10px;">✓</span>
                  </button>
                </div>
              </div>

              <!-- 发型选择 -->
              <div class="outfit-group">
                <div class="group-label">发型</div>
                <div class="group-options">
                  <button
                    v-for="hair in outfitOptions.live2dHairs"
                    :key="hair.id"
                    class="option-chip"
                    :class="{ active: live2dOutfit.hairId === hair.id }"
                    @click="applyLive2dOutfit({ ...live2dOutfit, hairId: hair.id, hairStyle: hair.style, hairColor: hair.color })"
                  >
                    {{ hair.name }}
                  </button>
                </div>
              </div>

              <!-- 服装选择 -->
              <div class="outfit-group">
                <div class="group-label">服装</div>
                <div class="group-options">
                  <button
                    v-for="cloth in outfitOptions.live2dClothes"
                    :key="cloth.id"
                    class="option-chip"
                    :class="{ active: live2dOutfit.clothId === cloth.id }"
                    @click="applyLive2dOutfit({ ...live2dOutfit, clothId: cloth.id, clothStyle: cloth.style, outfitColor: cloth.color, outfitAccent: cloth.accent, skirtColor: cloth.skirt })"
                  >
                    {{ cloth.name }}
                  </button>
                </div>
              </div>

              <!-- 袜子选择 -->
              <div class="outfit-group">
                <div class="group-label">袜子</div>
                <div class="group-options">
                  <button
                    v-for="sock in outfitOptions.live2dSocks"
                    :key="sock.id"
                    class="option-chip"
                    :class="{ active: live2dOutfit.sockId === sock.id }"
                    @click="applyLive2dOutfit({ ...live2dOutfit, sockId: sock.id, sockStyle: sock.style, sockColor: sock.color })"
                  >
                    {{ sock.name }}
                  </button>
                </div>
              </div>

              <!-- 鞋子选择 -->
              <div class="outfit-group">
                <div class="group-label">鞋子</div>
                <div class="group-options">
                  <button
                    v-for="shoe in outfitOptions.live2dShoes"
                    :key="shoe.id"
                    class="option-chip"
                    :class="{ active: live2dOutfit.shoeId === shoe.id }"
                    @click="applyLive2dOutfit({ ...live2dOutfit, shoeId: shoe.id, shoeStyle: shoe.style, shoeColor: shoe.color })"
                  >
                    {{ shoe.name }}
                  </button>
                </div>
              </div>

              <!-- 蝴蝶结样式 -->
              <div class="outfit-group">
                <div class="group-label">蝴蝶结</div>
                <div class="group-options">
                  <button
                    v-for="bow in outfitOptions.live2dBows"
                    :key="bow.id"
                    class="option-chip deco-chip"
                    :class="{ active: live2dOutfit.bowId === bow.id }"
                    @click="applyLive2dOutfit({ ...live2dOutfit, bowId: bow.id, bowStyle: bow.emoji, hasBow: true })"
                  >
                    {{ bow.emoji }}
                  </button>
                </div>
              </div>
              <!-- AI 图片换装（SadTalker 模式） -->
              <div v-if="currentAvatarType === 'sadtalker'" class="ai-avatar-section">
                <div class="group-label">🤖 AI 数字人换装</div>
                <div class="ai-avatar-controls">
                  <textarea 
                    v-model="aiPrompt" 
                    placeholder="描述你想要的数字人形象，如：一个穿传统汉服的女性导游，微笑，专业形象"
                    class="ai-prompt-input"
                    rows="3"
                  ></textarea>
                  <div class="ai-options">
                    <label class="gender-label">
                      <input type="radio" v-model="aiGender" value="female" /> 女性
                    </label>
                    <label class="gender-label">
                      <input type="radio" v-model="aiGender" value="male" /> 男性
                    </label>
                  </div>
                  <button 
                    class="ai-generate-btn" 
                    :disabled="!aiPrompt || isGeneratingAvatar"
                    @click="generateAiAvatar"
                  >
                    {{ isGeneratingAvatar ? '生成中...' : '🎨 生成AI形象' }}
                  </button>
                </div>

                <!-- 图片预览 -->
                <div v-if="generatedAvatarUrl" class="ai-avatar-preview">
                  <img :src="generatedAvatarUrl" alt="生成的数字人形象" class="preview-img" />
                  <div class="preview-actions">
                    <button class="confirm-btn" @click="confirmAiAvatar">✅ 确认使用</button>
                    <button class="regenerate-btn" @click="generateAiAvatar">🔄 重新生成</button>
                  </div>
                  <div v-if="isGeneratingVideos" class="generation-progress">
                    <div class="progress-text">{{ avatarProgress }}</div>
                    <div class="progress-bar">
                      <div class="progress-fill" :style="{ width: avatarProgressPercent + '%' }"></div>
                    </div>
                  </div>
                </div>
              </div>

            </template>
          </div>
        </transition>

        <!-- 数字人舞台 -->
        <div class="avatar-stage-inner"
             ref="avatarStageInner"
             :style="{
               left: charX + '%',
               top: charY + '%',
               /* translate(-50%, -100%) 使人物脚底对齐到 top 位置 */
               transform: `translate(-50%, -90%) scale(${charScale})`,
               transition: isMoving ? 'none' : 'transform 0.3s ease, opacity 0.2s ease'
             }"
        >
          <!-- ========== 数字人（三种类型切换） ========== -->
          <transition name="avatar-switch">
            <AvatarChibi
              v-if="currentAvatarType === 'chibi'"
              :outfit="currentOutfit"
              :talking="isTalking"
              :loading="isLoading"
              :blinking="isBlinking"
              :subtitle="currentSubtitle"
            />
          </transition>

          <!-- Live2D 漫画风 -->
          <transition name="avatar-switch">
            <AvatarLive2D
              v-if="currentAvatarType === 'live2d'"
              :talking="isTalking"
              :loading="isLoading"
              :blinking="isBlinking"
              :subtitle="currentSubtitle"
              :outfit="live2dOutfit"
            />
          </transition>

        <!-- 闭合 avatar-stage-inner -->
        </div>

        <!-- 数字人视频引擎（独立定位，占满区域，不随点击移动） -->
        <transition name="avatar-switch">
          <div v-if="isVideoEngine" class="sadtalker-stage">
            <div class="sadtalker-wrapper">
              <!-- 待机视频层：单个视频循环播放 -->
              <div class="sadtalker-idle" :class="{ 'idle-dimmed': sadtalkerPhase === 'speaking' }">
                <video
                  v-if="idleVideoSrc"
                  ref="idleVideoRef"
                  :src="idleVideoSrc"
                  muted
                  autoplay
                  playsinline
                  loop
                  preload="auto"
                  class="idle-video"
                  @play="onVideoPlayLog('idle', $event)"
                  @ended="onIdleVideoEnded"
                  @error="onIdleVideoError"
                ></video>
                <!-- fallback：没有任何待机视频时显示引擎基础照片 -->
                <div v-else class="idle-fallback">
                  <img v-if="engineBasePhotoUrl" :src="engineBasePhotoUrl" alt="数字人基础照片" class="idle-avatar" />
                  <img v-else-if="currentAvatarUrl" :src="currentAvatarUrl" alt="数字人" class="idle-avatar" />
                </div>
                <!-- idle 阶段显示欢迎提示 -->
                <div v-if="sadtalkerPhase === 'idle'" class="idle-hint">👋 您好，有什么可以帮您？</div>
              </div>

              <!-- 思考/生成中的遮罩层（覆盖在待机视频上方） -->
              <div v-if="sadtalkerPhase === 'thinking' || sadtalkerPhase === 'generating'" class="sadtalker-thinking-overlay">
                <div class="thinking-avatar">
                  <div class="generating-ring"></div>
                </div>
                <div class="generating-text">{{ sadtalkerPhase === 'thinking' ? 'AI正在思考...' : 'AI导览师正在生成讲解视频...' }}</div>
                <div class="thinking-dots"><span></span><span></span><span></span></div>
              </div>

              <!-- 讲解视频覆盖层：对话/开场视频播放 -->
              <div v-if="sadtalkerPhase === 'speaking' && avatarVideoUrl" class="sadtalker-video-overlay">
                <video
                  ref="sadtalkerVideoRef"
                  :src="avatarVideoUrl"
                  playsinline
                  preload="auto"
                  class="sadtalker-video"
                  @play="onVideoPlayLog('speaking', $event)"
                  @canplay="onVideoCanPlay"
                  @ended="onVideoEnded"
                  @error="onVideoError"
                ></video>
              </div>
            </div>
          </div>
        </transition>

      </section>

      <!-- ========== 右侧：交互区 ========== -->
      <section class="interaction-section" :class="{ expanded: chatPanelVisible }">

        <transition name="slide-from-right">
          <div v-show="chatPanelVisible" class="chat-panel" ref="chatPanel">
          <div class="chat-header">
            <h3>📖 智能问答</h3>
            <button class="clear-btn" @click="clearChat" :disabled="isLoading">清空</button>
          </div>
          <div class="chat-messages" ref="chatMessages">
            <div v-if="messages.length === 0" class="chat-empty">
              <p>开始对话吧</p>
            </div>
            <transition-group name="message" tag="div">
              <div
                v-for="msg in messages"
                :key="msg.id"
                class="message"
                :class="msg.role"
              >
                <div class="message-avatar" v-if="msg.role !== 'system'">
                  {{ msg.role === 'user' ? '👤' : '🤖' }}
                </div>
                <div class="message-bubble">
                  <p>{{ msg.content }}</p>
                  <span class="message-time">{{ msg.time }}</span>
                </div>
              </div>
            </transition-group>
          </div>
        </div>
        </transition>

        <!-- 语音/文字输入区 -->
        <div class="input-panel" v-show="chatPanelVisible">
          <div class="voice-status" v-if="voiceStatus">
            <div class="voice-wave">
              <span v-for="i in 5" :key="i"></span>
            </div>
            <span>{{ voiceStatus }}</span>
          </div>

          <!-- AI思考中提示 -->
          <div class="thinking-tip" v-if="isLoading">
            <div class="thinking-dots">
              <span></span><span></span><span></span>
            </div>
            <span>AI导览师正在思考中，请稍候...</span>
          </div>

          <div class="input-row">
            <input
              v-model="inputText"
              class="text-input"
              placeholder="触摸输入文字或点击麦克风语音提问..."
              @focus="showKeyboard = true"
              @keyup.enter="sendMessage"
              :disabled="isLoading"
            />
            <button
              class="voice-btn"
              :class="{ recording: isRecording, disabled: isLoading }"
              :disabled="isLoading"
              @touchstart.prevent="startVoice"
              @touchend.prevent="stopVoice"
              @mousedown="startVoice"
              @mouseup="stopVoice"
            >
              <span v-if="isRecording">🔴</span>
              <span v-else-if="isLoading">⏳</span>
              <span v-else>🎤</span>
            </button>
            <button v-if="isLoading" class="abort-btn" @click="abortGeneration" title="中止对话生成">
              ⏹️ 中止
            </button>
            <button v-else class="send-btn" @click="sendMessage" :disabled="!inputText">
              发送
            </button>
          </div>

          <!-- 预设问题快捷面板 -->
          <div class="quick-questions" v-if="!isLoading && chatPanelVisible">
            <button
              v-for="q in quickQuestions"
              :key="q"
              class="quick-btn"
              @click="askQuick(q)"
            >{{ q }}</button>
          </div>
        </div>

          <!-- 虚拟键盘 -->
        <div class="virtual-keyboard" v-if="showKeyboard && !isLoading && chatPanelVisible" @click.stop>
          <div class="keyboard-header">
            <span>⌨️ 屏幕键盘</span>
            <div class="keyboard-mode-btns">
              <button class="mode-btn" :class="{ active: keyboardMode === 'qwerty' }" @click="keyboardMode = 'qwerty'">
                ABC
              </button>
              <button class="mode-btn symbol-btn" :class="{ active: keyboardMode === 'symbol' }" @click="toggleSymbols">
                123#
              </button>
              <button class="lang-toggle" :class="{ active: inputMode === 'cn' }" @click="toggleInputMode">
                {{ inputMode === 'en' ? '🌐 中文' : '🌐 English' }}
              </button>
            </div>
            <button class="keyboard-close" @click="showKeyboard = false">收起</button>
          </div>
          
          <!-- 中文输入候选词区域 -->
          <div class="pinyin-area" v-if="inputMode === 'cn' && pinyinBuffer">
            <div class="pinyin-display">
              <span class="pinyin-text">{{ pinyinBuffer }}</span>
              <span class="pinyin-hint">{{ candidates.length > 0 ? '按数字键选词或点击' : '拼写中...' }}</span>
              <button class="clear-pinyin" @click="clearPinyin">清空</button>
            </div>
            <div class="candidate-words-wrapper" v-if="candidates.length > 0">
              <div class="candidate-words">
                <button 
                  v-for="(word, idx) in candidates" 
                  :key="idx" 
                  class="candidate-btn"
                  :class="{ selected: candidateIndex === idx }"
                  @click="selectCandidate(word)"
                >
                  <span class="candidate-num">{{ idx + 1 }}</span>
                  {{ word }}
                </button>
              </div>
            </div>
          </div>
          
          <!-- 主键盘内容 -->
          <div class="keyboard-content">
            <!-- ABC 字母键盘 -->
            <template v-if="keyboardMode === 'qwerty'">
              <!-- 数字行 -->
              <div class="keyboard-row number-row">
                <button v-for="key in numberKeys" :key="key" class="key num-key" @click="inputKey(key)">{{ key }}</button>
              </div>
              <!-- 第一行字母 -->
              <div class="keyboard-row">
                <button v-for="key in row1" :key="key" class="key letter-key" @click="inputKey(key)">
                  {{ isShifted ? key.toUpperCase() : key }}
                </button>
              </div>
              <!-- 第二行字母 -->
              <div class="keyboard-row">
                <button v-for="key in row2" :key="key" class="key letter-key" @click="inputKey(key)">
                  {{ isShifted ? key.toUpperCase() : key }}
                </button>
              </div>
              <!-- 第三行字母 + 功能键 -->
              <div class="keyboard-row">
                <button class="key func-key shift-key" :class="{ active: isShifted }" @click="handleShift">
                  <span>{{ isShifted ? '⬆' : '⇧' }}</span>
                </button>
                <button v-for="key in row3" :key="key" class="key letter-key" @click="inputKey(key)">
                  {{ isShifted ? key.toUpperCase() : key }}
                </button>
                <button class="key func-key backspace-key" @click="handleBackspace">⌫</button>
              </div>
              <!-- 第四行（符号和空格） -->
              <div class="keyboard-row">
                <button class="key func-key" @click="toggleSymbols">
                  {{ keyboardMode === 'symbol' ? 'ABC' : '123' }}
                </button>
                <button class="key space-key" @click="inputKey(' ')">
                  {{ inputMode === 'cn' ? '空格' : 'space' }}
                </button>
                <button class="key func-key" @click="inputKey('.')">.</button>
                <button class="key enter-key" @click="handleEnter">发送</button>
              </div>
            </template>
            
            <!-- 标点符号键盘 -->
            <template v-else>
              <!-- 第一行标点 -->
              <div class="keyboard-row symbol-row">
                <button v-for="key in symbolRow1" :key="key" class="key symbol-key" @click="inputKey(key)">{{ key }}</button>
              </div>
              <!-- 第二行标点 -->
              <div class="keyboard-row symbol-row">
                <button v-for="key in symbolRow2" :key="key" class="key symbol-key" @click="inputKey(key)">{{ key }}</button>
              </div>
              <!-- 第三行标点 -->
              <div class="keyboard-row symbol-row">
                <button v-for="key in symbolRow3" :key="key" class="key symbol-key" @click="inputKey(key)">{{ key }}</button>
              </div>
              <!-- 第四行 -->
              <div class="keyboard-row">
                <button class="key func-key" @click="toggleSymbols">返回ABC</button>
                <button class="key space-key" @click="inputKey(' ')">空格</button>
                <button class="key func-key" @click="inputKey(',')">,</button>
                <button class="key enter-key" @click="handleEnter">发送</button>
              </div>
            </template>
          </div>
        </div>
      </section>
    </main>

    <!-- 左侧景点展开/收起按钮 -->
    <button v-if="!isIdle" class="spot-toggle-btn" :class="{ expanded: spotPanelVisible }"
      @click.stop="toggleSpotPanel"
      @touchstart.stop.prevent="toggleSpotPanel">
      <span class="toggle-text">{{ spotPanelVisible ? '收起' : '景点' }}</span>
    </button>

    <!-- 右侧聊天展开/收起按钮 -->
    <!-- @click.stop 阻止事件冒泡到 kiosk-container 触发 resetIdle 干扰 -->
    <!-- @touchstart.stop.prevent 防止触摸屏 touchstart+click 双重触发 toggleChatPanel -->
    <button v-if="!isIdle" class="chat-toggle-btn" :class="{ expanded: chatPanelVisible }"
      @click.stop="toggleChatPanel"
      @touchstart.stop.prevent="toggleChatPanel">
      <span class="toggle-text">对话</span>
    </button>

    <!-- 景点信息侧边栏 -->
    <transition name="slide">
      <div class="spot-detail-panel" v-if="showSpotDetail && selectedSpot">
        <button class="close-panel" @click="showSpotDetail = false">✕</button>
        <h2>{{ selectedSpot.name }}</h2>
        <div class="spot-image-wrap">
          <img
            v-if="selectedSpot.image && !spotImageFailed"
            :src="selectedSpot.image"
            :alt="selectedSpot.name"
            class="spot-detail-image"
            @error="spotImageFailed = true"
          />
          <div v-else class="spot-icon-placeholder">
            <span class="spot-icon-large">{{ selectedSpot.icon || '🏔️' }}</span>
            <span class="spot-icon-label">{{ selectedSpot.name }}</span>
          </div>
        </div>
        <div class="spot-desc">{{ selectedSpot.description }}</div>
        <div class="spot-location" v-if="selectedSpot.location">
          <span class="location-icon">📌</span>
          <span>{{ selectedSpot.location }}</span>
        </div>
        <div class="spot-category-tag" v-if="selectedSpot.category">{{ selectedSpot.category }}</div>
        <div class="spot-meta">
          <div class="meta-item">
            <span class="meta-label">开放时间</span>
            <span>{{ selectedSpot.openTime }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">票价</span>
            <span>{{ selectedSpot.price }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">距您</span>
            <span>{{ selectedSpot.distance }}m</span>
          </div>
        </div>
        <button class="guide-btn" @click="startGuide(selectedSpot)">🎙️ 开始讲解</button>

        <!-- 景点评论区 -->
        <div class="spot-reviews-section">
          <div class="reviews-header">
            <span class="reviews-title">💬 游客评价</span>
            <span v-if="spotReviewAvg > 0" class="reviews-avg">
              ⭐ {{ spotReviewAvg }} ({{ spotReviewTotal }}条)
            </span>
          </div>
          <!-- 发表评论 -->
          <div class="review-form" v-if="touristUser && !userHasReviewed">
            <div class="review-stars">
              <span v-for="i in 5" :key="i" class="star-btn" :class="{ active: reviewRating >= i }"
                @click="reviewRating = i">★</span>
            </div>
            <div style="display: flex; gap: 6px; margin-top: 6px">
              <input v-model="reviewContent" class="review-input" placeholder="说说你的感受..." />
              <button class="review-submit-btn" @click="submitReview" :disabled="reviewRating === 0">发布</button>
            </div>
          </div>
          <div v-else-if="!touristUser" class="review-login-hint">
            <span>📝 <a href="#" @click.prevent="showTouristLogin = true">登录</a> 后即可评论</span>
          </div>
          <div v-else-if="userHasReviewed" class="review-login-hint">
            <span>✅ 您已评论过该景点</span>
          </div>
          <!-- 评论列表 -->
          <div class="reviews-list" v-if="spotReviews.length > 0">
            <div v-for="r in spotReviews" :key="r.id" class="review-item">
              <div class="review-item-header">
                <span class="reviewer-name">{{ r.nickname }}</span>
                <span class="review-stars-sm">{{ '★'.repeat(r.rating) }}{{ '☆'.repeat(5 - r.rating) }}</span>
                <span class="review-time">{{ formatReviewTime(r.created_at) }}</span>
              </div>
              <div class="review-content" v-if="r.content">{{ r.content }}</div>
            </div>
          </div>
          <div v-else class="reviews-empty">暂无评论，快来抢沙发吧~</div>
        </div>
      </div>
    </transition>

    <!-- 投诉建议弹窗 -->
    <transition name="fade">
      <div class="modal-overlay" v-if="showComplaintDialog" @click.self="showComplaintDialog = false">
        <div class="modal-card complaint-modal">
          <button class="modal-close" @click="showComplaintDialog = false">✕</button>
          <h3>📝 投诉与建议</h3>
          <div class="complaint-type-tabs">
            <button :class="{ active: complaintType === 'complaint' }" @click="complaintType = 'complaint'">投诉</button>
            <button :class="{ active: complaintType === 'suggestion' }" @click="complaintType = 'suggestion'">建议</button>
          </div>
          <select v-model="complaintCategory" class="complaint-select">
            <option value="环境">环境问题</option>
            <option value="服务">服务态度</option>
            <option value="设施">设施损坏</option>
            <option value="安全">安全隐患</option>
            <option value="其他">其他</option>
          </select>
          <input v-model="complaintTitle" class="modal-input" placeholder="标题（简短描述）" />
          <textarea v-model="complaintContent" class="modal-textarea" placeholder="请详细描述您的问题或建议..." rows="4"></textarea>
          <input v-model="complaintContact" class="modal-input" placeholder="联系方式（选填）" />
          <button class="modal-submit-btn" @click="submitComplaint" :disabled="!complaintTitle.trim() || !complaintContent.trim()">
            {{ complaintSubmitting ? '提交中...' : '提交' }}
          </button>
        </div>
      </div>
    </transition>

    <!-- 游客登录/注册弹窗 -->
    <transition name="fade">
      <div class="modal-overlay" v-if="showTouristLogin" @click.self="showTouristLogin = false">
        <div class="modal-card login-modal">
          <button class="modal-close" @click="showTouristLogin = false">✕</button>
          <h3>{{ isRegisterMode ? '📝 注册账号' : '👤 游客登录' }}</h3>
          <template v-if="isRegisterMode">
            <input v-model="regNickname" class="modal-input" placeholder="昵称（选填）" />
            <input v-model="regPhone" class="modal-input" placeholder="手机号" />
            <input v-model="regPassword" class="modal-input" type="password" placeholder="密码" />
            <button class="modal-submit-btn" @click="handleRegister" :disabled="!regPhone.trim() || !regPassword.trim()">
              注册
            </button>
            <div class="modal-switch">已有账号？<a href="#" @click.prevent="isRegisterMode = false">去登录</a></div>
          </template>
          <template v-else>
            <input v-model="loginPhone" class="modal-input" placeholder="手机号" />
            <input v-model="loginPassword" class="modal-input" type="password" placeholder="密码" />
            <button class="modal-submit-btn" @click="handleLogin" :disabled="!loginPhone.trim() || !loginPassword.trim()">
              登录
            </button>
            <div class="modal-switch">没有账号？<a href="#" @click.prevent="isRegisterMode = true">去注册</a></div>
          </template>
        </div>
      </div>
    </transition>

    <!-- 空闲屏保 -->
    <transition name="fade">
      <div class="screensaver" v-if="isIdle" @click="resetIdle">
        <div class="screensaver-content">
          <div class="ss-logo">🏔️</div>
          <h2>{{ scenicName }}</h2>
          <p>触摸屏幕开始智能导览</p>
          <div class="ss-wave">
            <span v-for="i in 8" :key="i"></span>
          </div>
        </div>
      </div>
    </transition>

    <!-- ===== 天气详情弹窗 ===== -->
    <WeatherPopup
      :weather="weatherData"
      :visible="showWeatherPopup"
      @close="showWeatherPopup = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, computed } from 'vue'
import { useKioskStore } from '../store/kioskStore'
import AvatarChibi from '../components/AvatarChibi.vue'
import AvatarLive2D from '../components/AvatarLive2D.vue'
import BaiduMapView from '../components/BaiduMapView.vue'
import Scenic2DMap from '../components/Scenic2DMap.vue'
import WeatherPopup from '../components/WeatherPopup.vue'
import { LINGSHAN_SPOTS, LINGSHAN_BOUNDS, LINGSHAN_CENTER } from '../data/lingshanSpots.js'
import { gpsToMap2D } from '../utils/coordTransform.js'

const store = useKioskStore()

// 全局词典变量（初始化为空）
let chineseDictionary = {}
let scenicWords = {}

// 加载外部词典
async function loadDictionary() {
  try {
    const response = await fetch('/dictionary.json')
    const data = await response.json()
    // 合并所有词典
    chineseDictionary = {
      ...data['单字'] || {},
      ...data['常用词'] || {},
      ...data['常用短句'] || {}
    }
    scenicWords = {
      ...data['景区词汇'] || {},
      ...data['地名'] || {}
    }
    console.log('词典加载成功，共', Object.keys(chineseDictionary).length + Object.keys(scenicWords).length, '词条')
  } catch (error) {
    console.error('词典加载失败:', error)
  }
}

// 响应式数据
const scenicName = ref('灵山胜境')
const currentSpot = ref('')
const currentTime = ref('')
const currentDate = ref('')
const weather = ref({ temp: 22, desc: '晴', icon: '☀️' })
const weatherData = ref(null)
const showWeatherPopup = ref(false)
let weatherTimer = null
const isConnected = ref(false)
const isTalking = ref(false)
const isBlinking = ref(false)
const isRecording = ref(false)
const isLoading = ref(false)
const isIdle = ref(false)
// ===== 游客登录/注册 =====
const showTouristLogin = ref(false)
const showTouristProfile = ref(false)
const isRegisterMode = ref(false)
const touristUser = ref(null) // { tourist_id, nickname }
const loginPhone = ref('')
const loginPassword = ref('')
const regPhone = ref('')
const regPassword = ref('')
const regNickname = ref('')

// ===== 投诉建议 =====
const showComplaintDialog = ref(false)
const complaintType = ref('suggestion')
const complaintCategory = ref('其他')
const complaintTitle = ref('')
const complaintContent = ref('')
const complaintContact = ref('')
const complaintSubmitting = ref(false)

// ===== 景点评论 =====
const spotReviews = ref([])
const spotReviewAvg = ref(0)
const spotReviewTotal = ref(0)
const reviewRating = ref(0)
const reviewContent = ref('')
const userHasReviewed = ref(false)

const showSpotDetail = ref(false)
const selectedSpot = ref(null)
const spotImageFailed = ref(false)  // 景点图片加载失败时回退到 emoji
const spotPanelVisible = ref(false)
const inputText = ref('')
const voiceStatus = ref('')
const currentSubtitle = ref('')
const avatarVideoUrl = ref('')
const sadtalkerPhase = ref('idle') // 'idle' | 'thinking' | 'generating' | 'speaking'
const welcomeText = ref('')  // 当前数字人的欢迎语
const avatarName = ref('')   // 当前数字人名称
const sadtalkerVideoRef = ref(null)
// 待机视频：单视频循环播放
const idleVideoSrc = ref('')   // 待机视频 URL
const idleVideoRef = ref(null)
const messages = ref([])
const chatMessages = ref(null)
const showOutfitPanel = ref(false)
// 聊天面板展开/收缩
const chatPanelVisible = ref(false)
// 防止欢迎语音重复播放
const hasGreeted = ref(false)
// 配置是否已加载（防止竞态：用户交互早于配置加载）
const configLoaded = ref(false)
// 配置加载完成前用户已交互 → 等配置就绪后自动触发开场
const pendingGreet = ref(false)
// 用户是否已交互（点击/触摸），用于浏览器自动播放策略
const userInteracted = ref(false)
// 音频提示：浏览器阻止自动播放时显示
const showAudioHint = ref(false)
// 开场视频是否正在播放（用于中断判断）
const isOpeningPlaying = ref(false)
// 当前正在播放的音频对象（用于停止上一个）
const currentAudio = ref(null)
// 中止控制器（用于中断正在进行的 AI 对话/视频生成）
const abortController = ref(null)
// 待机视频列表 & 当前播放的待机视频
const idleVideoList = ref([])
const currentAvatarUrl = ref('')    // 当前头像图片 URL（动态获取）
const engineBasePhotoUrl = ref('')  // 当前引擎基础照片 URL（待机视频缺失时降级使用）

// ========== AI 数字人换装 ==========
const aiPrompt = ref('')              // 用户选择的文件名（显示用）
const avatarFile = ref(null)          // 用户选择的文件对象
const avatarFileInputRef = ref(null)   // 文件 input 的 ref
const aiGender = ref('female')       // 性别选择：'male' | 'female'
const generatedAvatarUrl = ref('')   // 上传后的图片 URL
const generatedAvatarPath = ref('')  // 上传后的图片路径
const isGeneratingAvatar = ref(false) // 是否正在生成图片
const isGeneratingVideos = ref(false) // 是否正在生成视频
const avatarProgress = ref('')       // 视频生成进度描述
const avatarProgressPercent = ref(0)  // 视频生成进度百分比（0-100）

// ========== 人物类型切换 ==========
// 人物类型固定为数字人，由管理后台控制切换（仍用 ref 保持兼容）
const currentAvatarType = ref('wav2lip')  // 默认引擎与后端一致
const sadtalkerEnabled = ref(true) // 视频生成开关（所有引擎通用），从后端获取
const engineEnabledMap = ref({ wav2lip: true, musetalk: true, sadtalker: true }) // 引擎开关状态（手动开关）
// 是否为视频引擎（需引擎开关已开启 + 后端视频生成开关已开启）
const isVideoEngine = computed(() => {
  const eng = currentAvatarType.value
  return ['sadtalker', 'musetalk', 'wav2lip'].includes(eng) && engineEnabledMap.value[eng] !== false
})

// 引擎 → 视频 URL 前缀映射
const ENGINE_VIDEO_PREFIX = {
  sadtalker: '/sadtalker-videos',
  musetalk: '/musetalk-videos',
  wav2lip: '/wav2lip-videos',
}
function getEngineVideoPrefix() {
  const eng = currentAvatarType.value
  return ENGINE_VIDEO_PREFIX[eng] || '/wav2lip-videos'
}
const avatarStageInner = ref(null)
const avatarScaleMap = { sadtalker: 1.0, musetalk: 1.0, wav2lip: 1.0, live2d: 1.0, chibi: 2.45 }

// 切换景点面板展开/收缩（防抖：300ms内重复调用忽略）
// 互斥逻辑：景点展开时自动收缩对话，对话展开时自动收缩景点，但可以同时收缩
let _toggleSpotPanelLock = false
function toggleSpotPanel() {
  if (_toggleSpotPanelLock) return
  _toggleSpotPanelLock = true
  spotPanelVisible.value = !spotPanelVisible.value
  // 景点展开时，自动收缩对话面板
  if (spotPanelVisible.value && chatPanelVisible.value) {
    chatPanelVisible.value = false
  }
  setTimeout(() => { _toggleSpotPanelLock = false }, 300)
}

// 切换聊天面板展开/收缩（防抖：300ms内重复调用忽略）
let _toggleChatPanelLock = false
function toggleChatPanel() {
  if (_toggleChatPanelLock) return
  _toggleChatPanelLock = true
  chatPanelVisible.value = !chatPanelVisible.value
  // 对话展开时，自动收缩景点面板
  if (chatPanelVisible.value && spotPanelVisible.value) {
    spotPanelVisible.value = false
  }
  setTimeout(() => { _toggleChatPanelLock = false }, 300)
}

// ========== AI 数字人换装 ==========
// 文件选择处理
function onAvatarFileChange(event) {
  const file = event.target.files[0]
  if (file) {
    avatarFile.value = file
    aiPrompt.value = file.name
    // 即时预览本地图片
    const reader = new FileReader()
    reader.onload = (e) => {
      generatedAvatarUrl.value = e.target.result
      generatedAvatarPath.value = ''  // 还没上传，无路径
    }
    reader.readAsDataURL(file)
  }
}

// 上传图片（替代 AI 生成）
async function generateAiAvatar() {
  if (!avatarFile.value || isGeneratingAvatar.value) return
  
  isGeneratingAvatar.value = true
  
  try {
    console.log('[AI换装] 上传图片:', avatarFile.value.name)
    const formData = new FormData()
    formData.append('file', avatarFile.value)
    formData.append('gender', aiGender.value)
    
    const resp = await fetch('/avatar/upload-image', {
      method: 'POST',
      body: formData
    })
    
    if (!resp.ok) {
      const err = await resp.json()
      throw new Error(err.detail || '上传失败')
    }
    
    const data = await resp.json()
    if (data.success) {
      generatedAvatarUrl.value = data.image_url
      generatedAvatarPath.value = data.image_path
      console.log('[AI换装] ✅ 图片上传成功:', data.image_url)
    } else {
      throw new Error('上传失败')
    }
  } catch (e) {
    console.error('[AI换装] ❌ 图片上传失败:', e)
    alert('图片上传失败: ' + e.message)
  } finally {
    isGeneratingAvatar.value = false
  }
}

async function confirmAiAvatar() {
  if (!generatedAvatarPath.value || isGeneratingVideos.value) return
  
  isGeneratingVideos.value = true
  avatarProgress.value = '正在准备批量生成视频...'
  avatarProgressPercent.value = 0
  
  try {
    console.log('[AI换装] 确认头像，开始批量生成视频...')
    const formData = new FormData()
    formData.append('image_path', generatedAvatarPath.value)
    formData.append('gender', aiGender.value)
    
    const resp = await fetch('/avatar/confirm', {
      method: 'POST',
      body: formData
    })
    
    if (!resp.ok) {
      const err = await resp.json()
      throw new Error(err.detail || '确认失败')
    }
    
    const data = await resp.json()
    if (data.success) {
      console.log('[AI换装] ✅ 全部视频生成成功！')
      console.log('  开场白视频:', data.opening_video)
      console.log('  待机视频:', data.idle_videos)
      
      // 重置状态
      generatedAvatarUrl.value = ''
      generatedAvatarPath.value = ''
      avatarFile.value = null
      aiPrompt.value = ''
      if (avatarFileInputRef.value) avatarFileInputRef.value.value = ''

      // 刷新头像和待机视频
      await fetchCurrentAvatar()
      await fetchIdleVideos()
      initIdleDoubleBuffer()

      alert('✅ 数字人换装完成！\n\n已生成：\n- 1个开场白视频\n- 5个待机视频\n\n新形象已自动更新。')
    } else {
      throw new Error('确认失败')
    }
  } catch (e) {
    console.error('[AI换装] ❌ 视频生成失败:', e)
    alert('视频生成失败: ' + e.message)
  } finally {
    isGeneratingVideos.value = false
    avatarProgress.value = ''
    avatarProgressPercent.value = 0
  }
}
// 人物位置（百分比，相对于容器）
const charX = ref(50)  // 水平位置 0-100
const charY = ref(55)  // 垂直位置 0-100（值越大越靠下/越近）
const charScale = ref(1.0)  // 缩放（基于景深计算）
const isMoving = ref(false)  // 是否正在移动
const targetX = ref(50)
const targetY = ref(75)

// 景深范围配置
const depthConfig = ref({
  minY: 35,   // 最远处
  maxY: 95,   // 最近处
  minScale: 0.6,  // 最远时的最小缩放
  maxScale: 1.3   // 最近时的最大缩放
})

// 场景路径数据（从API获取）
const scenePaths = ref([])
const sceneObstacles = ref([])
const defaultPosition = ref({ x: 50, y: 80, scale: 1.0 })
const showPathHints = ref(false)  // 是否显示路径提示（调试用）

// 移动动画相关
let moveAnimationId = null

// 换装选项配置
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
  // 漫画风专属选项
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
  bowColors: [
    { id: 'bc1', color: '#ec4899' },
    { id: 'bc2', color: '#8b5cf6' },
    { id: 'bc3', color: '#3b82f6' },
    { id: 'bc4', color: '#22c55e' },
    { id: 'bc5', color: '#eab308' },
    { id: 'bc6', color: '#ef4444' },
    { id: 'bc7', color: '#f8fafc' },
    { id: 'bc8', color: '#1f2937' },
  ],
}

// 当前装扮
const currentOutfit = ref({
  hairId: 'h1',
  clothId: 'c1',
  decoId: 'd1',
  hairStyle: 'bun',
  hairColor: '#3d2000',
  outfitBg: 'linear-gradient(180deg, #7dd3fc 0%, #0284c7 100%)',
  accentColor: '#0369a1',
  collarColor: '#e0f2fe',
  decoration: '🌸',
})

// 漫画风当前装扮
const live2dOutfit = ref({
  hairId: 'lh1',
  hairStyle: 'long-straight',
  clothId: 'lc1',
  clothStyle: 'dress',
  decoId: 'ld1',
  sockId: 'ls1',
  sockStyle: 'long',
  shoeId: 'lsh1',
  shoeStyle: 'mary-jane',
  irisId: 'le1',
  skinId: 'ls2',
  hairColor: '#7c3aed',
  irisColor: '#8b5cf6',
  skinColor: '#ffe0cc',
  outfitColor: '#e879f9',
  outfitAccent: '#a855f7',
  skirtColor: '#d946ef',
  ornament: '🌸',
  hasBow: true,
  bowId: 'lb1',
  bowStyle: '🎀',
  bowColorId: 'bc1',
  bowColor: '#ec4899',
  sockColor: '#f5f5f5',
  shoeColor: '#581c87',
})

// 景点数据（含2D地图坐标 mapX/mapY + GPS坐标 lat/lng，基于灵山胜境实际空间布局：南→北中轴线）
const nearbySpots = ref([...LINGSHAN_SPOTS])

// 景点视图模式：2d 2D导览图 / baidu 百度实景地图 / list 列表视图
const spotViewMode = ref('2d')

// 百度地图配置
const baiduMapsAk = ref('')
const baiduMapCenter = ref({ ...LINGSHAN_CENTER })

const quickQuestions = ref([
  '景区开放时间', '今天有什么活动', '推荐游览路线',
  '停车场在哪里', '餐厅在哪里', '厕所怎么走',
])

// ========== 虚拟键盘 ==========
const showKeyboard = ref(false)
const isShifted = ref(false)
const isSymbolMode = ref(false)
const inputMode = ref('cn')  // 'en' 英文模式, 'cn' 中文模式
const keyboardMode = ref('qwerty')  // 'qwerty' 字母键盘, 'symbol' 标点符号键盘

// 拼音输入相关
const pinyinBuffer = ref('')  // 当前输入的拼音
const candidates = ref([])  // 候选词列表
const candidateIndex = ref(-1)  // 当前选中的候选词索引

// 键盘按键布局
const numberKeys = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '0']
const row1 = ['q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p']
const row2 = ['a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l']
const row3 = ['z', 'x', 'c', 'v', 'b', 'n', 'm']

// 标点符号键盘布局（三行）
const symbolRow1 = ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')']
const symbolRow2 = ['-', '=', '+', '[', ']', '{', '}', '|', '\\', '/']
const symbolRow3 = [':', ';', '"', "'", '<', '>', ',', '.', '?', '~']

// 简化的中文词典和拼音映射（常用词汇 - 扩展多字词库）
// 注意：词典已移至 public/dictionary.json，通过 loadDictionary() 动态加载
// 以下是备用词典（词典加载失败时使用）
chineseDictionary = {
  // 备用词典
  // 单字
  'ni': ['你', '呢', '泥', '妮', '拟'],
  'hao': ['好', '号', '浩', '皓', '昊'],
  'shi': ['是', '时', '市', '试', '事'],
  'de': ['的', '得', '地'],
  'wo': ['我', '握', '卧'],
  'ta': ['他', '她', '它'],
  'men': ['们'],
  'zhe': ['这', '着'],
  'na': ['那', '哪', '纳'],
  'li': ['里', '理', '力', '利'],
  'zhi': ['知', '之', '只', '直'],
  'dao': ['到', '道', '导'],
  'ke': ['可', '科', '课', '客'],
  'yi': ['一', '已', '以', '意'],
  'ge': ['个', '各', '歌'],
  'zhong': ['中', '重', '种'],
  'guo': ['过', '国', '果'],
  'sheng': ['生', '声', '省', '胜'],
  'qi': ['起', '去', '气', '期'],
  'xing': ['行', '星', '性', '兴'],
  'tian': ['天', '田', '甜'],
  'di': ['地', '的', '第', '底'],
  'you': ['有', '游', '优', '又'],
  'qu': ['去', '区', '取', '曲'],
  'shui': ['谁', '水', '睡'],
  'shuo': ['说', '硕'],
  'hen': ['很', '恨'],
  'zui': ['最', '罪'],
  'chang': ['常', '长', '场'],
  'ren': ['人', '任', '认'],
  'zhan': ['站', '占', '展'],
  'ji': ['几', '机', '记', '己'],
  'wei': ['为', '位', '未', '围'],
  'mei': ['没', '美', '每'],
  'hao': ['好', '号', '浩', '皓', '昊'],
  'jiu': ['就', '久', '救'],
  'kan': ['看', '刊', '砍'],
  'ting': ['听', '停', '庭'],
  'zuo': ['坐', '作', '做', '左'],
  'chu': ['出', '处', '初'],
  'lai': ['来', '赖'],
  'zai': ['在', '再'],
  'neng': ['能', '而'],
  'xiao': ['小', '消', '笑', '效'],
  'nan': ['南', '难', '男'],
  'dui': ['对', '队'],
  'hu': ['湖', '户', '呼'],
  'yin': ['因', '银', '音', '引'],
  'yu': ['于', '与', '雨', '语', '域'],
  'he': ['和', '河', '合', '何'],
  'men': ['们', '门'],
  'bian': ['边', '便', '变'],
  'bian': ['边', '便', '变'],
  'shui': ['谁', '水', '睡'],
  
  // 双字词
  'zhidao': ['知道', '指导'],
  'jingqu': ['景区', '警区'],
  'kaifang': ['开放'],
  'shijian': ['时间', '实践'],
  'luyou': ['旅游', '路由'],
  'jintian': ['今天'],
  'mingtian': ['明天'],
  'zuijin': ['最近'],
  'tingche': ['停车'],
  'canting': ['餐厅'],
  'cesuo': ['厕所'],
  'jieshao': ['介绍'],
  'jingdian': ['景点'],
  'menpiao': ['门票'],
  'jiage': ['价格'],
  'zhandian': ['站点'],
  'luxian': ['路线'],
  'daoyou': ['导游'],
  'teshu': ['特殊', '特色'],
  'meili': ['美丽'],
  'piaoliang': ['漂亮'],
  'youmei': ['优美'],
  'haowan': ['好玩'],
  'zheli': ['这里'],
  'nali': ['哪里'],
  'zenme': ['怎么'],
  'weishenme': ['为什么'],
  'shenme': ['什么'],
  'duoshao': ['多少'],
  'zaijian': ['再见'],
  'xiexie': ['谢谢'],
  'buhaooyi': ['不客气'],
  'qingwen': ['请问'],
  'bushouqi': ['不好意思'],
  'youyisi': ['有意思'],
  'zhidao': ['知道'],
  'zhengzai': ['正在'],
  'shibushi': ['是不是'],
  'zuihao': ['最好'],
  'keshi': ['可是', '可是'],
  'zhidao': ['知道'],
  'zhongyu': ['终于'],
  'zhunbei': ['准备'],
  'yijing': ['已经'],
  'tongyi': ['同意', '统一'],
  'bijiao': ['比较'],
  'feichang': ['非常'],
  'jixu': ['继续'],
  'kaishi': ['开始'],
  'jieshu': ['结束'],
  'tingzhi': ['停止'],
  'bangzhu': ['帮助'],
  'xuyao': ['需要'],
  'jieshou': ['接受'],
  'fanshi': ['凡是'],
  'jihu': ['几乎'],
  'ganxie': ['感谢'],
  'lingwa': ['另外'],
  'zhengli': ['整理'],
  'baohan': ['包含'],
  'gengai': ['更改'],
  'tongzhi': ['通知'],
  'fanyi': ['翻译'],
  'xuexi': ['学习'],
  'gongzuo': ['工作'],
  'shenghuo': ['生活'],
  'jiaoyu': ['教育'],
  'jishu': ['技术'],
  'gushi': ['故事', '股市'],
  'qingjing': ['情景', '情景'],
  'jiqiqiao': ['机器'],
  
  // 三字词组
  'zaishengli': ['在哪里'],
  'zenmeban': ['怎么办'],
  'shibabide': ['是吧'],
  'buhaoyisi': ['不好意思'],
  'jingquyu': ['景区'],
  'jingdianhe': ['景点'],
  'yinianshi': ['仪式'],
  'tingchewei': ['停车位'],
  'cantingzai': ['餐厅在'],
  'hanyuliao': ['韩语'],
  'zhongguoyu': ['中国语'],
  'yingyuyan': ['英语'],
  'ribenyu': ['日语'],
  'hanyuyan': ['韩语'],
  'yuqingkuang': ['语情况'],
  'shengyinfu': ['声语气'],
  'liulanliang': ['浏览量'],
  'gengxinla': ['更新啦'],
  'zhongyukaishi': ['终于开始'],
  'zuihaode': ['最好的'],
  'keshide': ['可是的'],
  'zhidaode': ['知道的'],
  'yiyangde': ['一样的'],
  'feichangde': ['非常'],
  'jixiangde': ['吉祥'],
  'zhenzhide': ['值得'],
  'shengyizhong': ['生意中'],
  'zuixinde': ['最新的'],
  'kekaode': ['可靠的'],
  'biaozhide': ['标准的'],
  'zhongyudian': ['终电'],
  'zhongguo': ['中国'],
  'beijingshi': ['北京是'],
  'shanghaishi': ['上海市'],
  'guangzhoushi': ['广州市'],
  'shenzhen': ['深圳'],
  'hangzhou': ['杭州'],
  'xiamen': ['厦门'],
  'chengdu': ['成都'],
  'chongqing': ['重庆'],
  'wuxi': ['无锡'],
  'lingshan': ['灵山'],
  'lingshanshengjing': ['灵山胜境'],
  'lingshandafo': ['灵山大佛'],
  'suzhou': ['苏州'],
  'nanjing': ['南京'],
  'wuhan': ['武汉'],
  'xian': ['西安'],
  'dalian': ['大连'],
  'qingdao': ['青岛'],
  'zhengzhou': ['郑州'],
  'changsha': ['长沙'],
  'hefei': ['合肥'],
  'fuzhou': ['福州'],
  'xian': ['西安'],
  'jilin': ['吉林'],
  'harbin': ['哈尔滨'],
  'shenyang': ['沈阳'],
  'changchun': ['长春'],
  'tianjin': ['天津'],
  'shijiazhuang': ['石家庄'],
  'taiyuan': ['太原'],
  'hohhot': ['呼和浩特'],
  'baotou': ['包头'],
  'nanchang': ['南昌'],
  'jinan': ['济南'],
  'qingdao': ['青岛'],
  'yantai': ['烟台'],
  'zhengzhou': ['郑州'],
  'luoyang': ['洛阳'],
  'kaifeng': ['开封'],
  'huangshan': ['黄山'],
  'wuyuan': ['婺源'],
  'lijiang': ['丽江'],
  'guilin': ['桂林'],
  'yangshuo': ['阳朔'],
  'xishuangbanna': ['西双版纳'],
  'shangrila': ['香格里拉'],
  'lijiang': ['丽江'],
  'dali': ['大理'],
  'kunming': ['昆明'],
  'xian': ['西安'],
  'pingyao': ['平遥'],
  'wuyuan': ['婺源'],
  'huizhou': ['徽州'],
  'guangzhou': ['广州'],
  'shanghai': ['上海'],
  'beijing': ['北京'],
  'shenzhen': ['深圳'],
  'hangzhou': ['杭州'],
  'suzhou': ['苏州'],
  'nanjing': ['南京'],
  'chengdu': ['成都'],
  'xian': ['西安'],
  'chongqing': ['重庆'],
  'wuhan': ['武汉'],
  'tianjin': ['天津'],
  
  // 常见多字词组（用于分词识别）
  'nihao': ['你好'],
  'zaojian': ['再见'],
  'tingche': ['停车'],
  'canting': ['餐厅'],
  'cesuo': ['厕所'],
  'jingqu': ['景区'],
  'jingdian': ['景点'],
  'jieshao': ['介绍'],
  'zhidao': ['知道'],
  'zenme': ['怎么'],
  'shenme': ['什么'],
  'duoshao': ['多少'],
  'zaijian': ['再见'],
  'xiexie': ['谢谢'],
  'buhaooyi': ['不客气'],
  'qingwen': ['请问'],
  'nali': ['哪里'],
  'zheli': ['这里'],
  'jintian': ['今天'],
  'mingtian': ['明天'],
  'zuijin': ['最近'],
  'feichang': ['非常'],
  'zuihao': ['最好'],
  'piaoliang': ['漂亮'],
  'youmei': ['优美'],
  'meili': ['美丽'],
  'haowan': ['好玩'],
  'tianqi': ['天气'],
  'yubao': ['预报'],
  'kaifang': ['开放'],
  'shijian': ['时间'],
  'luyou': ['旅游'],
  'daoyou': ['导游'],
  'menpiao': ['门票'],
  'jiage': ['价格'],
  'zhandian': ['站点'],
  'luxian': ['路线'],
  'xiuxian': ['休闲'],
  'dujia': ['度假'],
  'youlan': ['游览'],
  'tingzhi': ['停止'],
  'bangzhu': ['帮助'],
  'xuyao': ['需要'],
  'zhunbei': ['准备'],
  'kaishi': ['开始'],
  'jieshu': ['结束'],
  'jixu': ['继续'],
  'zuixin': ['最新'],
  'zuimei': ['最美'],
  'feichang': ['非常'],
  'zhenzheng': ['真正'],
  'zhongyao': ['重要'],
  'teshu': ['特殊'],
  'biaozhun': ['标准'],
  'zhengque': ['正确'],
  'lijie': ['理解'],
  'zhidaojia': ['指导'],
  'zhidaole': ['知道了'],
  'bushouqi': ['不好意思'],
  'feichangganxie': ['非常感谢'],
  'zhongguo': ['中国'],
  'beijing': ['北京'],
  'shanghai': ['上海'],
  'guangzhou': ['广州'],
  'shenzhen': ['深圳'],
  'hangzhou': ['杭州'],
  'chengdu': ['成都'],
  'xian': ['西安'],
  'chongqing': ['重庆'],
  'wuhan': ['武汉'],
  'tianjin': ['天津'],
  'nanjing': ['南京'],
  'suzhou': ['苏州'],
  'xiamen': ['厦门'],
  'lijiang': ['丽江'],
  'guilin': ['桂林'],
  'huangshan': ['黄山'],
  'qingdao': ['青岛'],
  'dalian': ['大连'],

  // 四字及以上词组
  'qingwenjingqu': ['请问景区'],
  'jingqugailue': ['景区概略'],
  'jingqujingdian': ['景区景点'],
  'gonglujiaotong': ['公路交通'],
  'zuihaojiedao': ['最好街道'],
  'feichangpiaoliang': ['非常漂亮'],
  'zhongyaojieshao': ['重要介绍'],
  'yuqingbaogao': ['雨情报告'],
  'tianqiyubao': ['天气预报'],
  'jintianqingkuang': ['今天情况'],
  'mingtianzhidao': ['明天知道'],
  'tingchezheli': ['停车这里'],
  'cantingzhonglei': ['餐厅种类'],
  'menpiaoyouhui': ['门票优惠'],
  'luyoujihua': ['旅游计划'],
  'xianluqingkuang': ['线路情况'],
  'daoyoujieshao': ['导游介绍'],
  'jingquteseliao': ['景区特色'],
  'piaoliangfengjing': ['漂亮风景'],
  'meilishanshui': ['美丽山水'],
  'youmeijingdian': ['优美景点'],
  'haowanyoumei': ['好玩优美'],
  'zheliyoubiede': ['这里有的'],
  'nalihaowan': ['哪里好玩'],
  'zenmeyoumei': ['怎么优美'],
  'shenmejingdian': ['什么景点'],
  'shenmehaoowan': ['什么好玩'],
  'zenmebijiao': ['怎么比较'],
  'zhidaoma': ['知道吗'],
  'zhidaojintian': ['知道今天'],
  'nengbangzhuwo': ['能帮助我'],
  'xiexiedaji': ['谢谢大家'],
  'bushouqile': ['不好意思'],
  'qinggengxin': ['请更新'],
  'feichangganxie': ['非常感谢'],
  'buhaoyisiyin': ['不好意思'],
  'buhaoyisin': ['不好意思'],
  'zhidaole': ['知道了'],
  'zuimeiode': ['最美的'],
  'feichangbang': ['非常棒'],
  'zhenzhongyu': ['真终于'],
  'shibushiyou': ['是不是有'],
  'jintiantianqi': ['今天天气'],
  'mingtiantianqi': ['明天天气'],
  'zhongguojingqu': ['中国景区'],
  'zhongyaogushi': ['重要故事'],
  'jingqugonglue': ['景区攻略'],
  'menpiaoyhui': ['门票优惠'],
  'teseliaojies': ['特色介绍'],
  'zuixinfengge': ['最新风格'],
  'bijiaobangde': ['比较棒的'],
  'feichangbiede': ['非常别'],
  'zhidaobiede': ['知道别'],
  'shenmeshihou': ['什么时候'],
  'duoshaoqian': ['多少钱'],
  'zenmezuode': ['怎么做的'],
  'naliyoude': ['哪里有的'],
  'zheliyoude': ['这里有的'],
  'youyuanshi': ['有园是'],
  'shangdiandao': ['商点到'],
  'xiawushengyi': ['下午生意'],
  'shangwushengyi': ['上午生意'],
  'zaiciganxie': ['再次感谢'],
  'zhongyujiedao': ['终于街道'],
  'feichangzhidao': ['非常知道'],

  // 更多实用短句（用于分词组合）
  'zaishenme': ['在什么'],
  'zenmequ': ['怎么去'],
  'zenmezou': ['怎么走'],
  'youyuann': ['有园'],
  'haowanle': ['好玩了'],
  'piaoliangde': ['漂亮的'],
  'jingdiande': ['景点的'],
  'zhidaobuzhidao': ['知道不知道'],
  'zhidaojintian': ['知道今天'],
  'zhidaomintian': ['知道明天'],
  'henshufu': ['很舒服'],
  'hengaoxing': ['很高兴'],
  'henbang': ['很棒'],
  'henyouyisi': ['很有意思'],
  'henpiaoliang': ['很漂亮'],
  'feichangbang': ['非常棒'],
  'zhendezhendao': ['真知道'],
  'zhidaodao': ['知道到'],
  'nengbuneng': ['能不能'],
  'keyibukeyi': ['可不可以'],
  'buzhidao': ['不知道'],
  'bushao': ['不少'],
  'bushihao': ['不是好'],
  'bukuai': ['不快'],
  'buneng': ['不能'],
  'bushuo': ['不说'],
  'buyong': ['不用'],
  'bushichi': ['不吃'],
  'bushuijiao': ['不睡觉'],
  'zhidaoma': ['知道吗'],
  'henbangde': ['很棒的'],
  'zhidaoya': ['知道呀'],
  'zhidaoai': ['知道哎'],
  'zhidaoe': ['知道诶'],
  'zhidaole': ['知道了'],
  'zhidaolema': ['知道吗'],
  'zhidaobuhui': ['知道不会'],
  'zhidaocuo': ['知道错'],
  'zhidaoxianzai': ['知道现在'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
  'zhidaole': ['知道了'],
  'zhidaojintian': ['知道今天'],
  'zhidaomingtian': ['知道明天'],
}

// 景区相关词库（扩展 - 备用）
scenicWords = {
  // 备用景区词库
  'guangchang': ['广场'],
  'juchang': ['剧场'],
  'tingchechang': ['停车场'],
  'canting': ['餐厅'],
  'wenhua': ['文化'],
  'minjian': ['民间'],
  'liushi': ['历史'],
  'fengjing': ['风景'],
  'shanshui': ['山水'],
  'senlin': ['森林'],
  'haibin': ['海滨'],
  'xiyang': ['夕阳'],
  'chaosheng': ['超盛'],
  'fanguan': ['饭店'],
  'jiudian': ['酒店'],
  'gongyuan': ['公园'],
  'gongjiao': ['公交'],
  'ditie': ['地铁'],
  'huoche': ['火车'],
  'feiji': ['飞机'],
  'zhan': ['站'],
  'piao': ['票'],
  'jia': ['价'],
  'lu': ['路'],
  'che': ['车'],
  'men': ['门'],
  'qu': ['区'],
  'pian': ['片'],
  'shan': ['山'],
  'shui': ['水'],
  'hua': ['花'],
  'cao': ['草'],
  'shu': ['树'],
  'gu': ['古'],
  'cheng': ['城'],
  'zhai': ['寨'],
  'zhen': ['镇'],
  'cun': ['村'],
  'xian': ['县'],
  'qu': ['区'],
  
  // 景区双字词
  'guangchang': ['广场'],
  'jingdian': ['景点'],
  'fengjing': ['风景'],
  'shanshui': ['山水'],
  'senlin': ['森林'],
  'haibin': ['海滨'],
  'tianye': ['田野'],
  'caoyuan': ['草原'],
  'shamo': ['沙漠'],
  'gulou': ['古楼'],
  'gucheng': ['古城'],
  'guzhen': ['古镇'],
  'guzhai': ['古寨'],
  'shuixiang': ['水乡'],
  'haiwan': ['海湾'],
  'haidiao': ['海岛'],
  'haitan': ['海滩'],
  'lüyou': ['旅游'],
  'dujia': ['度假'],
  'xiuxian': ['休闲'],
  'kanguan': ['看管'],
  'canguan': ['参观'],
  'youlan': ['游览'],
  'daoyou': ['导游'],
  'jiedai': ['接待'],
  'zhumai': ['主迈'],
  'tingche': ['停车'],
  'menpiao': ['门票'],
  'jiage': ['价格'],
  'youhui': ['优惠'],
  'taocan': ['套餐'],
  'dingzhi': ['定制'],
  'zhanlue': ['战略'],
  'luxian': ['路线'],
  'tusheng': ['图胜'],
  'shengdi': ['圣地'],
  'wenhua': ['文化'],
  'lishi': ['历史'],
  'minzu': ['民族'],
  'chuantong': ['传统'],
  'yishu': ['艺术'],
  'jianzhu': ['建筑'],
  'ziran': ['自然'],
  'tese': ['特色'],
  'meijing': ['美景'],
  'xianhua': ['鲜花'],
  'shengtai': ['生态'],
  'qihou': ['气候'],
  'jijie': ['季节'],
  'tiwen': ['提问'],
  'huida': ['回答'],
  'xiangqing': ['详情'],
  'gengxin': ['更新'],
  'zhuanjia': ['专家'],
  'jieshao': ['介绍'],
  'zhidao': ['指导'],
  'zhunbei': ['准备'],
  'kaishi': ['开始'],
  'jieshu': ['结束'],
  'tingzhi': ['停止'],
  'jixu': ['继续'],
  'bangzhu': ['帮助'],
  'xuyao': ['需要'],
  'zhengzai': ['正在'],
  
  // 景区三字词组
  'shanqingshui': ['山清水'],
  'fengjingqu': ['风景去'],
  'lvyouqu': ['旅游区'],
  'dujiaqu': ['度假区'],
  'senlingong': ['森林公园'],
  'haibinlu': ['海滨路'],
  'haiwanwan': ['海湾湾'],
  'guchengqu': ['古城区'],
  'lishiwenhua': ['历史文化'],
  'minzufengqing': ['民族风情'],
  'yishugong': ['艺术宫'],
  'jianzhumei': ['建筑美'],
  'ziranshengtai': ['自然生态'],
  'tianqiyubao': ['天气预报'],
  'menpiaojiage': ['门票价格'],
  'youhuijiage': ['优惠价格'],
  'xiuxiandujia': ['休闲度假'],
  'lvyoujingdian': ['旅游景点'],
  'jingquluxian': ['景区路线'],
  'daoyouyu': ['导游语'],
  'canguanxian': ['参观线'],
  'youlanluxian': ['游览路线'],
  'xiangxijieshao': ['详细介绍'],
  'feichangmei': ['非常美'],
  'zhenzhidequ': ['真正的'],
  'zuihaodequ': ['最好的'],
  'piaoliangde': ['漂亮的'],
  'shenmijing': ['什么景'],
  'naliyouqu': ['哪里有区'],
  'zenmequ': ['怎么去'],
  'zuigaobian': ['最高便'],
  'zuiliangde': ['最凉的'],
  'zuihaoqu': ['最好区'],
  'zhongguo': ['中国'],
  'beijingshi': ['北京市'],
  'shanghaishi': ['上海市'],
  'guangzhoushi': ['广州市'],
  'shenzhen': ['深圳'],
  'hangzhou': ['杭州'],
  'xiamen': ['厦门'],
  'chengdu': ['成都'],
  'chongqing': ['重庆'],
  'wuxi': ['无锡'],
  'lingshan': ['灵山'],
  'lingshanshengjing': ['灵山胜境'],
  'lingshandafo': ['灵山大佛'],
  'suzhou': ['苏州'],
  'nanjing': ['南京'],
  'wuhan': ['武汉'],
  'xianshi': ['先是'],
  'dalianshi': ['大连市'],
  'qingdaoshi': ['青岛市'],
  'zhengzhou': ['郑州'],
  'changshashi': ['长沙市'],
  'hefeishi': ['合肥市'],
  'fuzhoushi': ['福州市'],
  'guilinshi': ['桂林市'],
  'lijiangshi': ['丽江时'],
  'wuyuanxian': ['婺源县'],
  
  // 景区四字及以上词组
  'shanqingshuixiu': ['山清水秀'],
  'fengjingyoumei': ['风景优美'],
  'shanshuifengguang': ['山水风光'],
  'senlinbaohuqu': ['森林保护区'],
  'haibinfengjingqu': ['海滨风景区'],
  'guchengfengqing': ['古城风情'],
  'lishiwenhuayu': ['历史文化与'],
  'minzufengqingyou': ['民族风情游'],
  'chuantongjianzhu': ['传统建筑'],
  'ziranshengtaigu': ['自然生态古'],
  'tianqiyubaogao': ['天气预报报'],
  'menpiaoyouhui': ['门票优惠'],
  'youhuijiagedui': ['优惠价格对'],
  'xiuxiandujiaqu': ['休闲度假区'],
  'lvyoujingdianpai': ['旅游景点排'],
  'jingquluxianjian': ['景区路线建'],
  'daoyoujieshao': ['导游介绍'],
  'canguanguanli': ['参观管理'],
  'youlanluxiantui': ['游览路线推'],
  'xiangxijieshao': ['详细介绍'],
  'feichangpiaoliang': ['非常漂亮'],
  'zhenzhidebiede': ['真值得别'],
  'zuihaodejiedao': ['最好的街道'],
  'piaoliangfengjing': ['漂亮风景'],
  'shenmejingdian': ['什么景点'],
  'naliyoumeili': ['哪里有美丽'],
  'zenmeyouyisi': ['怎么有意思'],
  'youmeijingdian': ['优美景点'],
  'zuixinfengqing': ['最新风情'],
  'bijiaoqingchu': ['比较清楚'],
  'feichangbangde': ['非常棒的'],
  'zhongguojingqu': ['中国景区'],
  'zhongyaojieshao': ['重要介绍'],
  'ganxienindeguan': ['感谢您的关'],
  'bushouqigaosu': ['不好意思告'],
  'zhidaojintian': ['知道今天'],
  'shenmeshihou': ['什么时候'],
  'zenmezhidao': ['怎么知道'],
  'nengbangzhuma': ['能帮助吗'],
  'qingbangzhuwo': ['请帮助我'],
  'feichangganxie': ['非常感谢'],
  'zhongyujieshao': ['终于介绍'],

  // ========== 扩展常用词库 ==========
  // 常用动词和动作
  'laile': ['来了'],
  'guoqu': ['过去'],
  'xianzai': ['现在'],
  'zou': ['走'],
  'pao': ['跑'],
  'zhan': ['站'],
  'zuo': ['坐'],
  'tang': ['躺'],
  'wan': ['玩'],
  'chi': ['吃'],
  'he': ['喝'],
  'shui': ['睡'],
  'xue': ['学'],
  'wan': ['玩'],
  'zuoye': ['作业'],
  'gongzuo': ['工作'],
  'xihuan': ['喜欢'],
  'tongyi': ['同意'],
  'faxian': ['发现'],
  'zhidao': ['知道'],
  'yihan': ['遗憾'],
  'shengqi': ['生气'],
  'gaoxing': ['高兴'],
  'nan guo': ['难过'],
  'haopla': ['好啦'],
  'zhidao': ['知道'],

  // 常用形容词
  'da': ['大'],
  'xiao': ['小'],
  'chang': ['长'],
  'duan': ['短'],
  'gao': ['高'],
  'ai': ['矮'],
  'pang': ['胖'],
  'shou': ['瘦'],
  'xin': ['新'],
  'jiu': ['旧'],
  'kuai': ['快'],
  'man': ['慢'],
  're': ['热'],
  'leng': ['冷'],
  'tian': ['甜'],
  'suan': ['酸'],
  'la': ['辣'],
  'xian': ['咸'],
  'dan': ['淡'],
  'xiang': ['香'],
  'chou': ['臭'],

  // 常用名词
  'shui': ['水'],
  'cha': ['茶'],
  'jiu': ['酒'],
  'kuangquanshui': ['矿泉水'],
  'putao': ['葡萄'],
  'pingguo': ['苹果'],
  'xiangjiao': ['香蕉'],
  'chengzi': ['橙子'],
  'caomei': ['草莓'],
  'xigu': ['西瓜'],
  'taozi': ['桃子'],
  'limu': ['梨'],
  'mangguo': ['芒果'],
  'boluo': ['菠萝'],
  'shejian': ['舌尖'],
  'fancai': ['饭菜'],
  'zhongcan': ['中餐'],
  'xican': ['西餐'],
  'kuaican': ['快餐'],
  'baoshi': ['宝石'],
  'zhubao': ['珠宝'],
  'yifu': ['衣服'],
  'xie': ['鞋'],
  'bao': ['包'],
  'mianbao': ['面包'],
  'jitui': ['鸡腿'],
  'kaifei': ['咖啡'],
  'niunai': ['牛奶'],
  'doujiang': ['豆浆'],
  'baozi': ['包子'],
  'mantou': ['馒头'],
  'jiaozi': ['饺子'],
  'baofan': ['饱饭'],
  'fan': ['饭'],
  'cai': ['菜'],
  'rou': ['肉'],
  'yu': ['鱼'],
  'jirou': ['鸡肉'],
  'zhurou': ['猪肉'],
  'niurou': ['牛肉'],
  'yangrou': ['羊肉'],
  'xiaren': ['虾仁'],
  'qiezi': ['茄子'],
  'huatong': ['花菜'],
  'baicai': ['白菜'],
  'tudou': ['土豆'],
  'fanshu': ['番薯'],
  'shuiguo': ['水果'],
  'shucai': ['蔬菜'],
  'haixian': ['海鲜'],
  'tiantian': ['甜甜'],
  'tianpin': ['甜品'],
  'binggan': ['饼干'],
  'qiaokeli': ['巧克力'],
  'bingqilin': ['冰淇淋'],
  'shutong': ['薯条'],
  'jirengan': ['鸡肝'],
  'yangrouchuan': ['羊肉串'],
  'zhagandong': ['炸豆腐'],
  'baochang': ['报唱'],
  'chaohua': ['抄化'],
  'chou': ['臭'],

  // 常用疑问词
  'weishenme': ['为什么'],
  'zenmeban': ['怎么办'],
  'zenmeyang': ['怎么样'],
  'zenmeme': ['怎么么'],
  'naer': ['哪儿'],
  'nar': ['哪儿'],
  'na': ['哪'],
  'ji': ['几'],
  'duoshao': ['多少'],
  'jiu': ['旧'],
  'haojiu': ['好久'],
  'jiuneng': ['就能'],
  'jiuyao': ['就要'],
  'jiushi': ['就是'],
  'bushihao': ['不是好'],
  'zhidaobuhui': ['知道不会'],
  'zhidaocuo': ['知道错'],
  'zhidaoxianzai': ['知道现在'],

  // 常用短句
  'nihao': ['你好'],
  'zaijian': ['再见'],
  'xiexie': ['谢谢'],
  'zhidaole': ['知道了'],
  'keai': ['可爱'],
  'piaoliang': ['漂亮'],
  'bang': ['棒'],
  'xihuan': ['喜欢'],
  'henbang': ['很棒'],
  'feichangbang': ['非常棒'],
  'youmei': ['优美'],
  'meili': ['美丽'],
  'wanmei': ['完美'],
  'zhenzheng': ['真正'],
  'bucuo': ['不错'],
  'zhende': ['真的'],
  'shima': ['是吗'],
  'duima': ['对吗'],
  'zuima': ['罪吗'],
  'hen': ['很'],
  'taidu': ['态度'],
  'zhidaoma': ['知道吗'],

  // 更多景区相关
  'jingqu': ['景区'],
  'menpiao': ['门票'],
  'jiage': ['价格'],
  'youhui': ['优惠'],
  'kaifang': ['开放'],
  'shijian': ['时间'],
  'tingche': ['停车'],
  'canting': ['餐厅'],
  'jiudian': ['酒店'],
  'teshu': ['特殊'],
  'tese': ['特色'],
  'zhonglei': ['种类'],
  'zhonglei': ['种类'],
  'pinzhi': ['品质'],
  'jiazhi': ['价值'],
  'jiqiao': ['技巧'],
  'zhinan': ['指南'],
  'gonglue': ['攻略'],
  'tupian': ['图片'],
  'shipin': ['视频'],
  'jieshao': ['介绍'],
  'daoyou': ['导游'],
  'wenhua': ['文化'],
  'lishi': ['历史'],
  'fengjing': ['风景'],
  'meijing': ['美景'],
  'shanshui': ['山水'],
  'senlin': ['森林'],
  'haibin': ['海滨'],
  'gucheng': ['古城'],
  'guzhen': ['古镇'],
  'gongyuan': ['公园'],
  'baishui': ['拜水'],
  'wenda': ['问道'],
  'qingfeng': ['清风'],
  'mingyue': ['明月'],
  'chuntian': ['春天'],
  'xiatian': ['夏天'],
  'qiutian': ['秋天'],
  'dongtian': ['冬天'],
  'qingchen': ['清晨'],
  'zhongwu': ['中午'],
  'huanghun': ['黄昏'],
  'yewan': ['夜晚'],
  'wanfa': ['玩法'],
  'luxian': ['路线'],
  'jiedao': ['街道'],
  'gongjiao': ['公交'],
  'ditie': ['地铁'],
  'zhan': ['站'],
  'piao': ['票'],
  'jia': ['价'],
  'lu': ['路'],
  'che': ['车'],
  'feiji': ['飞机'],
  'huoche': ['火车'],
  'lunchuan': ['轮船'],
  'chuanbo': ['船舶'],
  'zhuSu': ['住宿'],
  'zh sus': ['住宿'],
  'jiulou': ['酒楼'],
  'fandian': ['饭店'],
  'xiaochi': ['小吃'],
  'tongzhi': ['通知'],
  'xinwen': ['新闻'],
  'tianqi': ['天气'],
  'yubao': ['预报'],
  'wenxintishi': ['温馨提示'],
  'zhuyishixiang': ['注意事项'],
  'kaifangshijian': ['开放时间'],
  'tingcheshourongfei': ['停车收费'],
  'lianxidianhua': ['联系电话'],
  'fuwutiaokuan': ['服务条款'],
  'gengxinshijian': ['更新时间'],

  // 常用连接词和助词
  'de': ['的'],
  'le': ['了'],
  'ma': ['吗'],
  'ba': ['吧'],
  'a': ['啊'],
  'ne': ['呢'],
  'ya': ['呀'],
  'ou': ['哦'],
  'ei': ['诶'],
  'na': ['哪'],
  'hai': ['还'],
  'ye': ['也'],
  'dou': ['都'],
  'jiu': ['就'],
  'cai': ['才'],
  'gen': ['跟'],
  'he': ['和'],
  'huozhe': ['或者'],
  'danshi': ['但是'],
  'yinwei': ['因为'],
  'suoyi': ['所以'],
  'ruguo': ['如果'],
  'jishi': ['即使'],
  'wulun': ['无论'],
  'zhengyinwei': ['正因'],
  'bingqie': ['并且'],
  'chule': ['除了'],
  'haisheng': ['还行'],
  'chule': ['除了'],
}

// 合并词库
const allDictionary = { ...chineseDictionary, ...scenicWords }

// ========== 拼音分词与候选词（改进版） ==========

// 标准拼音音节表（覆盖所有现代汉语拼音音节，不含声调）
const PINYIN_SYLLABLES = new Set([
  'a','ai','an','ang','ao',
  'ba','bai','ban','bang','bao','bei','ben','beng','bi','bian','biao','bie','bin','bing','bo','bu',
  'ca','cai','can','cang','cao','ce','cen','ceng','cha','chai','chan','chang','chao','che','chen','cheng','chi','chong','chou','chu','chua','chuai','chuan','chuang','chui','chun','chuo','ci','cong','cou','cu','cuan','cui','cun','cuo',
  'da','dai','dan','dang','dao','de','dei','den','deng','di','dian','diao','die','ding','diu','dong','dou','du','duan','dui','dun','duo',
  'e','ei','en','eng','er',
  'fa','fan','fang','fei','fen','feng','fo','fou','fu',
  'ga','gai','gan','gang','gao','ge','gei','gen','geng','gong','gou','gu','gua','guai','guan','guang','gui','gun','guo',
  'ha','hai','han','hang','hao','he','hei','hen','heng','hong','hou','hu','hua','huai','huan','huang','hui','hun','huo',
  'ji','jia','jian','jiang','jiao','jie','jin','jing','jiong','jiu','ju','juan','jue','jun',
  'ka','kai','kan','kang','kao','ke','ken','keng','kong','kou','ku','kua','kuai','kuan','kuang','kui','kun','kuo',
  'la','lai','lan','lang','lao','le','lei','leng','li','lia','lian','liang','liao','lie','lin','ling','liu','long','lou','lu','luan','lun','luo','lv','lve',
  'ma','mai','man','mang','mao','me','mei','men','meng','mi','mian','miao','mie','min','ming','miu','mo','mou','mu',
  'na','nai','nan','nang','nao','ne','nei','nen','neng','ni','nian','niang','niao','nie','nin','ning','niu','nong','nou','nu','nuan','nuo','nv','nve',
  'o','ou',
  'pa','pai','pan','pang','pao','pei','pen','peng','pi','pian','piao','pie','pin','ping','po','pou','pu',
  'qi','qia','qian','qiang','qiao','qie','qin','qing','qiong','qiu','qu','quan','que','qun',
  'ran','rang','rao','re','ren','reng','ri','rong','rou','ru','ruan','rui','run','ruo',
  'sa','sai','san','sang','sao','se','sen','seng','sha','shai','shan','shang','shao','she','shei','shen','sheng','shi','shou','shu','shua','shuai','shuan','shuang','shui','shun','shuo','si','song','sou','su','suan','sui','sun','suo',
  'ta','tai','tan','tang','tao','te','teng','ti','tian','tiao','tie','ting','tong','tou','tu','tuan','tui','tun','tuo',
  'wa','wai','wan','wang','wei','wen','weng','wo','wu',
  'xi','xia','xian','xiang','xiao','xie','xin','xing','xiong','xiu','xu','xuan','xue','xun',
  'ya','yan','yang','yao','ye','yi','yin','ying','yo','yong','you','yu','yuan','yue','yun',
  'za','zai','zan','zang','zao','ze','zei','zen','zeng','zha','zhai','zhan','zhang','zhao','zhe','zhei','zhen','zheng','zhi','zhong','zhou','zhu','zhua','zhuai','zhuan','zhuang','zhui','zhun','zhuo','zi','zong','zou','zu','zuan','zui','zun','zuo',
])

// 基础拼音→汉字映射（常用高频字，每个音节取最高频的1-5个字）
const PINYIN_BASE = {
  'a': ['啊','阿'],
  'ai': ['爱','艾','哀','挨','矮'],
  'an': ['安','按','暗','岸','案'],
  'ang': ['昂'],
  'ao': ['奥','傲','澳','凹','熬'],
  'ba': ['吧','把','八','爸','巴'],
  'bai': ['百','白','败','摆','拜'],
  'ban': ['办','半','班','版','般'],
  'bang': ['帮','棒','绑','傍','邦'],
  'bao': ['报','包','保','宝','暴'],
  'bei': ['被','北','备','背','杯'],
  'ben': ['本','奔','笨'],
  'beng': ['蹦','崩','绷'],
  'bi': ['比','必','笔','闭','币'],
  'bian': ['便','变','边','编','遍'],
  'biao': ['表','标','彪','飙'],
  'bie': ['别'],
  'bin': ['宾','斌','彬','滨'],
  'bing': ['并','病','兵','冰','饼'],
  'bo': ['波','博','播','薄','伯'],
  'bu': ['不','部','步','布','补'],
  'ca': ['擦'],
  'cai': ['才','财','采','彩','菜'],
  'can': ['参','餐','残','惨','灿'],
  'cang': ['藏','仓','苍'],
  'cao': ['草','操','曹'],
  'ce': ['策','侧','测','册'],
  'cen': ['参'],
  'ceng': ['曾','层'],
  'cha': ['查','差','茶','察','插'],
  'chai': ['差','拆','柴'],
  'chan': ['产','场','长','颤','缠'],
  'chang': ['长','场','常','唱','厂'],
  'chao': ['超','潮','炒','抄','朝'],
  'che': ['车','彻','撤','扯'],
  'chen': ['陈','称','沉','晨','衬'],
  'cheng': ['成','城','程','称','承'],
  'chi': ['吃','持','尺','迟','赤'],
  'chong': ['重','冲','充','崇','虫'],
  'chou': ['抽','愁','丑','筹','仇'],
  'chu': ['出','处','初','除','楚'],
  'chuai': ['揣'],
  'chuan': ['传','穿','船','川','串'],
  'chuang': ['创','窗','床','闯'],
  'chui': ['吹','垂','锤'],
  'chun': ['春','纯','唇','醇'],
  'chuo': ['戳'],
  'ci': ['此','次','词','刺','辞'],
  'cong': ['从','聪','丛','葱'],
  'cou': ['凑'],
  'cu': ['促','粗','醋'],
  'cuan': ['窜','攒'],
  'cui': ['催','脆','翠','崔'],
  'cun': ['存','村','寸'],
  'cuo': ['错','措','搓'],
  'da': ['大','打','达','答','搭'],
  'dai': ['带','代','待','戴','贷'],
  'dan': ['但','单','蛋','担','淡'],
  'dang': ['当','党','档','荡'],
  'dao': ['到','道','刀','导','倒'],
  'de': ['的','得','德'],
  'dei': ['得'],
  'deng': ['等','登','灯','邓','瞪'],
  'di': ['地','第','低','底','弟'],
  'dian': ['点','电','店','典','垫'],
  'diao': ['掉','调','吊','雕','钓'],
  'die': ['跌','叠','爹','碟'],
  'ding': ['定','顶','订','丁','盯'],
  'diu': ['丢'],
  'dong': ['动','东','懂','冬','洞'],
  'dou': ['都','豆','斗','逗','兜'],
  'du': ['都','读','度','独','毒'],
  'duan': ['段','短','断','端','锻'],
  'dui': ['对','队','堆','兑'],
  'dun': ['吨','顿','蹲','盾','敦'],
  'duo': ['多','夺','朵','躲','堕'],
  'e': ['额','俄','鹅','恶','饿'],
  'ei': ['诶'],
  'en': ['恩'],
  'er': ['而','二','儿','耳'],
  'fa': ['发','法','罚','乏','伐'],
  'fan': ['反','饭','翻','范','犯'],
  'fang': ['方','放','房','防','访'],
  'fei': ['非','飞','费','肥','废'],
  'fen': ['分','份','粉','奋','纷'],
  'feng': ['风','封','丰','峰','冯'],
  'fo': ['佛'],
  'fou': ['否'],
  'fu': ['服','夫','父','复','福'],
  'ga': ['嘎'],
  'gai': ['改','该','盖','概'],
  'gan': ['感','干','敢','赶','甘'],
  'gang': ['港','刚','钢','岗','纲'],
  'gao': ['高','告','搞','糕','稿'],
  'ge': ['个','各','歌','格','哥'],
  'gei': ['给'],
  'gen': ['跟','根','艮'],
  'geng': ['更','耕','庚','梗'],
  'gong': ['工','公','功','共','供'],
  'gou': ['够','狗','构','购','沟'],
  'gu': ['古','故','顾','股','鼓'],
  'gua': ['挂','刮','瓜','寡'],
  'guai': ['怪','拐','乖'],
  'guan': ['关','管','观','官','馆'],
  'guang': ['光','广','逛'],
  'gui': ['贵','归','鬼','规','桂'],
  'gun': ['滚','棍','衮'],
  'guo': ['过','国','果','锅','郭'],
  'ha': ['哈'],
  'hai': ['还','海','害','孩','嗨'],
  'han': ['汉','韩','喊','含','寒'],
  'hang': ['行','航','杭'],
  'hao': ['好','号','毫','豪','浩'],
  'he': ['和','合','河','何','喝'],
  'hei': ['黑','嘿'],
  'hen': ['很','恨','狠','痕'],
  'heng': ['横','衡','恒','哼'],
  'hong': ['红','宏','洪','鸿','虹'],
  'hou': ['后','候','厚','猴','喉'],
  'hu': ['户','护','湖','互','乎'],
  'hua': ['化','华','话','花','划'],
  'huai': ['坏','怀','淮','徊'],
  'huan': ['还','换','环','欢','患'],
  'huang': ['黄','皇','慌','晃','煌'],
  'hui': ['会','回','汇','惠','灰'],
  'hun': ['混','婚','魂','昏','浑'],
  'huo': ['或','活','火','货','获'],
  'ji': ['几','机','记','计','基'],
  'jia': ['家','加','假','价','架'],
  'jian': ['见','件','间','建','检'],
  'jiang': ['将','江','讲','奖','降'],
  'jiao': ['教','交','叫','角','较'],
  'jie': ['接','界','解','结','节'],
  'jin': ['进','今','近','金','尽'],
  'jing': ['经','景','精','京','境'],
  'jiong': ['窘','炯'],
  'jiu': ['就','九','久','酒','旧'],
  'ju': ['具','据','局','举','剧'],
  'juan': ['卷','捐','娟','倦'],
  'jue': ['决','绝','觉','角','掘'],
  'jun': ['军','均','君','俊','菌'],
  'ka': ['卡','咖','喀'],
  'kai': ['开','凯','概','楷'],
  'kan': ['看','刊','砍','堪'],
  'kang': ['康','抗','慷','炕'],
  'kao': ['考','靠','烤','拷'],
  'ke': ['可','科','客','课','刻'],
  'ken': ['肯','恳','啃'],
  'keng': ['坑','铿'],
  'kong': ['空','控','孔','恐'],
  'kou': ['口','扣','寇','抠'],
  'ku': ['苦','库','哭','酷','裤'],
  'kua': ['跨','夸','垮'],
  'kuai': ['快','块','筷','会'],
  'kuan': ['款','宽'],
  'kuang': ['况','矿','框','狂','旷'],
  'kui': ['亏','愧','溃','葵','魁'],
  'kun': ['困','昆','捆','坤'],
  'kuo': ['括','扩','阔'],
  'la': ['拉','啦','辣','蜡'],
  'lai': ['来','莱','赖'],
  'lan': ['蓝','兰','栏','览','烂'],
  'lang': ['浪','朗','狼','郎'],
  'lao': ['老','劳','牢','涝','佬'],
  'le': ['了','乐','勒'],
  'lei': ['类','累','雷','泪','磊'],
  'leng': ['冷','楞','棱'],
  'li': ['里','理','力','利','立'],
  'lia': ['俩'],
  'lian': ['连','联','脸','练','链'],
  'liang': ['两','量','亮','良','辆'],
  'liao': ['了','料','聊','疗','辽'],
  'lie': ['列','烈','裂','猎','劣'],
  'lin': ['林','临','邻','淋','琳'],
  'ling': ['领','令','零','灵','另'],
  'liu': ['流','六','留','刘','柳'],
  'long': ['龙','隆','笼','拢','聋'],
  'lou': ['楼','漏','露','娄','搂'],
  'lu': ['路','陆','录','露','炉'],
  'luan': ['乱','卵','峦'],
  'lun': ['论','轮','伦','沦'],
  'luo': ['落','罗','络','洛','骆'],
  'lv': ['律','旅','绿','率','虑'],
  'lve': ['略','掠'],
  'ma': ['吗','妈','马','麻','码'],
  'mai': ['买','卖','麦','迈','埋'],
  'man': ['满','慢','漫','瞒','蔓'],
  'mang': ['忙','盲','茫','蟒'],
  'mao': ['毛','猫','冒','矛','贸'],
  'me': ['么'],
  'mei': ['没','美','每','妹','媒'],
  'men': ['们','门','闷'],
  'meng': ['梦','猛','蒙','盟','孟'],
  'mi': ['米','密','迷','秘','蜜'],
  'mian': ['面','免','棉','眠','绵'],
  'miao': ['苗','秒','妙','描','庙'],
  'mie': ['灭','蔑'],
  'min': ['民','敏','闽','皿'],
  'ming': ['名','明','命','鸣','铭'],
  'mo': ['末','陌','默','模','磨'],
  'mou': ['某','谋','牟'],
  'mu': ['目','木','母','幕','牧'],
  'na': ['那','拿','哪','纳','娜'],
  'nai': ['乃','奶','耐','奈'],
  'nan': ['难','南','男'],
  'nao': ['闹','脑','恼'],
  'ne': ['呢'],
  'nei': ['内','那'],
  'nen': ['嫩'],
  'neng': ['能'],
  'ni': ['你','尼','呢','拟','逆'],
  'nian': ['年','念','粘','碾'],
  'niang': ['娘','酿'],
  'niao': ['鸟','尿'],
  'nie': ['捏','聂','孽'],
  'nin': ['您'],
  'ning': ['宁','凝','拧','狞'],
  'niu': ['牛','纽','扭'],
  'nong': ['农','弄','浓'],
  'nu': ['努','怒','奴'],
  'nuan': ['暖'],
  'nuo': ['诺','挪'],
  'nv': ['女'],
  'nve': ['虐','疟'],
  'o': ['哦'],
  'ou': ['偶','欧','殴','呕'],
  'pa': ['怕','爬','帕','趴'],
  'pai': ['排','牌','拍','派','徘'],
  'pan': ['判','盘','盼','潘','攀'],
  'pang': ['旁','胖','庞'],
  'pao': ['跑','泡','炮','抛'],
  'pei': ['配','培','陪','赔','佩'],
  'pen': ['盆','喷'],
  'peng': ['朋','碰','棚','膨','蓬'],
  'pi': ['批','皮','屁','匹','脾'],
  'pian': ['片','便','篇','偏','骗'],
  'piao': ['票','飘','漂','瓢'],
  'pie': ['撇'],
  'pin': ['品','频','拼','贫','聘'],
  'ping': ['平','评','瓶','凭','苹'],
  'po': ['破','迫','坡','颇','泊'],
  'pou': ['剖'],
  'pu': ['普','铺','扑','朴','谱'],
  'qi': ['起','其','七','期','气'],
  'qia': ['恰','掐'],
  'qian': ['前','千','钱','签','迁'],
  'qiang': ['强','枪','墙','抢','腔'],
  'qiao': ['桥','巧','敲','乔','瞧'],
  'qie': ['且','切','窃','怯'],
  'qin': ['亲','勤','秦','琴','侵'],
  'qing': ['情','请','清','青','轻'],
  'qiong': ['穷','琼','穹'],
  'qiu': ['求','球','秋','邱','丘'],
  'qu': ['去','取','区','曲','趣'],
  'quan': ['全','权','圈','劝','泉'],
  'que': ['却','确','缺','雀','鹊'],
  'qun': ['群','裙'],
  'ran': ['然','染','燃','冉'],
  'rang': ['让','嚷','壤','瓤'],
  'rao': ['绕','扰','饶'],
  're': ['热','惹'],
  'ren': ['人','任','认','仁','忍'],
  'reng': ['仍','扔'],
  'ri': ['日'],
  'rong': ['容','融','荣','绒','溶'],
  'rou': ['肉','柔','揉'],
  'ru': ['如','入','乳','儒','辱'],
  'ruan': ['软','阮'],
  'rui': ['瑞','锐','睿'],
  'run': ['润','闰'],
  'ruo': ['若','弱'],
  'sa': ['撒','洒','萨'],
  'sai': ['赛','塞','腮'],
  'san': ['三','散','伞'],
  'sang': ['桑','嗓','丧'],
  'sao': ['扫','骚','嫂'],
  'se': ['色','塞','涩','瑟'],
  'sen': ['森'],
  'seng': ['僧'],
  'sha': ['杀','沙','傻','啥','砂'],
  'shai': ['晒','筛'],
  'shan': ['山','善','闪','衫','珊'],
  'shang': ['上','商','伤','尚','赏'],
  'shao': ['少','绍','烧','稍','绍'],
  'she': ['设','社','射','涉','蛇'],
  'shei': ['谁'],
  'shen': ['什','身','深','神','审'],
  'sheng': ['生','声','省','升','胜'],
  'shi': ['是','时','市','事','十'],
  'shou': ['手','受','首','收','售'],
  'shu': ['书','数','术','输','属'],
  'shua': ['刷','耍'],
  'shuai': ['帅','摔','衰','甩'],
  'shuan': ['栓','拴'],
  'shuang': ['双','爽','霜'],
  'shui': ['水','谁','睡','税'],
  'shun': ['顺','瞬','舜'],
  'shuo': ['说','硕','烁'],
  'si': ['四','思','死','丝','似'],
  'song': ['送','松','宋','颂','耸'],
  'sou': ['搜','艘','嗽'],
  'su': ['速','素','苏','诉','塑'],
  'suan': ['算','酸','蒜'],
  'sui': ['随','岁','虽','碎','遂'],
  'sun': ['孙','损','笋'],
  'suo': ['所','所','锁','索','缩'],
  'ta': ['他','她','它','踏','塔'],
  'tai': ['太','台','态','抬','泰'],
  'tan': ['谈','弹','探','叹','贪'],
  'tang': ['堂','汤','唐','躺','糖'],
  'tao': ['套','讨','逃','陶','淘'],
  'te': ['特'],
  'teng': ['疼','腾','藤'],
  'ti': ['提','题','体','替','踢'],
  'tian': ['天','田','甜','填','添'],
  'tiao': ['条','调','跳','挑','眺'],
  'tie': ['铁','贴','帖'],
  'ting': ['听','停','庭','厅','挺'],
  'tong': ['同','通','统','痛','童'],
  'tou': ['头','投','透','偷'],
  'tu': ['图','土','突','途','涂'],
  'tuan': ['团','湍'],
  'tui': ['推','退','腿','褪'],
  'tun': ['吞','屯','囤'],
  'tuo': ['脱','托','拖','妥','拓'],
  'wa': ['瓦','挖','娃','蛙','洼'],
  'wai': ['外','歪','崴'],
  'wan': ['万','完','晚','玩','湾'],
  'wang': ['网','王','往','望','忘'],
  'wei': ['为','位','未','微','围'],
  'wen': ['文','问','温','闻','稳'],
  'weng': ['翁','瓮'],
  'wo': ['我','握','卧','窝','涡'],
  'wu': ['无','五','务','物','武'],
  'xi': ['西','细','系','息','希'],
  'xia': ['下','夏','吓','峡','狭'],
  'xian': ['先','现','线','显','县'],
  'xiang': ['想','向','相','像','项'],
  'xiao': ['小','笑','消','效','校'],
  'xie': ['写','些','谢','鞋','协'],
  'xin': ['新','心','信','辛','欣'],
  'xing': ['行','性','星','兴','形'],
  'xiong': ['兄','雄','胸','凶','熊'],
  'xiu': ['修','休','秀','袖','绣'],
  'xu': ['需','许','续','须','徐'],
  'xuan': ['选','宣','旋','悬','玄'],
  'xue': ['学','雪','血','穴','薛'],
  'xun': ['寻','讯','训','迅','巡'],
  'ya': ['亚','压','牙','呀','雅'],
  'yan': ['眼','言','验','研','严'],
  'yang': ['样','阳','养','洋','央'],
  'yao': ['要','药','腰','摇','咬'],
  'ye': ['也','业','夜','叶','页'],
  'yi': ['一','已','以','意','义'],
  'yin': ['因','音','银','引','印'],
  'ying': ['应','影','英','营','映'],
  'yo': ['哟'],
  'yong': ['用','永','拥','勇','涌'],
  'you': ['有','又','由','油','游'],
  'yu': ['于','与','语','雨','域'],
  'yuan': ['元','原','远','院','愿'],
  'yue': ['月','约','越','乐','阅'],
  'yun': ['运','云','允','韵','孕'],
  'za': ['杂','砸','咋'],
  'zai': ['在','再','载','灾','仔'],
  'zan': ['赞','咱','攒','暂'],
  'zang': ['藏','脏','葬'],
  'zao': ['早','造','遭','糟','枣'],
  'ze': ['则','责','择','泽'],
  'zei': ['贼'],
  'zen': ['怎'],
  'zeng': ['增','赠','曾','憎'],
  'zha': ['炸','扎','渣','闸','眨'],
  'zhai': ['债','宅','窄','摘','寨'],
  'zhan': ['站','占','战','展','粘'],
  'zhang': ['张','长','章','掌','涨'],
  'zhao': ['找','照','招','赵','召'],
  'zhe': ['这','着','者','折','哲'],
  'zhei': ['这'],
  'zhen': ['真','镇','针','震','诊'],
  'zheng': ['正','政','整','证','争'],
  'zhi': ['之','知','只','制','指'],
  'zhong': ['中','重','种','终','众'],
  'zhou': ['周','州','洲','轴','粥'],
  'zhu': ['主','住','注','助','珠'],
  'zhua': ['抓'],
  'zhuai': ['拽'],
  'zhuan': ['转','专','赚','砖','撰'],
  'zhuang': ['装','状','庄','壮','撞'],
  'zhui': ['追','坠','缀'],
  'zhun': ['准'],
  'zhuo': ['桌','着','捉','卓','琢'],
  'zi': ['自','子','资','字','紫'],
  'zong': ['总','宗','综','纵','踪'],
  'zou': ['走','奏','邹'],
  'zu': ['组','足','族','租','阻'],
  'zuan': ['钻','纂'],
  'zui': ['最','罪','醉','嘴'],
  'zun': ['尊','遵'],
  'zuo': ['做','作','坐','左','座'],
}

// 合并自定义词典到基础映射
function buildFullDictionary() {
  const merged = {}
  // 先复制基础音节表
  for (const [key, chars] of Object.entries(PINYIN_BASE)) {
    merged[key] = [...chars]
  }
  // 合并外部词典（chineseDictionary、scenicWords）
  for (const [key, words] of Object.entries(allDictionary)) {
    if (merged[key]) {
      for (const w of words) {
        if (!merged[key].includes(w)) merged[key].push(w)
      }
    } else {
      merged[key] = [...words]
    }
  }
  return merged
}

// 全词典（基础+自定义）
const FULL_DICT = buildFullDictionary()

// 前向最大匹配分词（贪心算法，从左到右匹配最长音节）
function segmentPinyin(pinyin) {
  if (!pinyin || pinyin.length === 0) return []

  const lower = pinyin.toLowerCase()
  const segments = []
  let i = 0

  while (i < lower.length) {
    let matched = false
    // 从最长6字符开始尝试匹配（最长的拼音音节如 "zhuang" = 6字符）
    const maxLen = Math.min(6, lower.length - i)
    for (let len = maxLen; len >= 1; len--) {
      const candidate = lower.slice(i, i + len)
      if (PINYIN_SYLLABLES.has(candidate)) {
        // 是有效拼音音节，查找对应的汉字
        const chars = FULL_DICT[candidate] || [candidate]
        segments.push({ pinyin: candidate, chars })
        i += len
        matched = true
        break
      }
    }
    if (!matched) {
      // 无法匹配为有效音节，直接保留原文
      segments.push({ pinyin: lower[i], chars: [lower[i]] })
      i++
    }
  }

  return segments
}

// 获取候选词（基于拼音缓冲）
function getCandidates(pinyin) {
  if (!pinyin) return []

  const lower = pinyin.toLowerCase()
  const candidates = []

  // 1. 分词后获取组合候选
  const segments = segmentPinyin(lower)
  if (segments.length > 0) {
    // 显示完整组合（每个音节取第一个字）
    const fullWord = segments.map(s => s.chars[0]).join('')
    if (fullWord && fullWord !== lower) {
      candidates.push(fullWord)
    }
    // 如果只有一个有效音节，显示该音节的所有候选字
    if (segments.length === 1 && segments[0].chars.length > 1) {
      for (const ch of segments[0].chars) {
        if (!candidates.includes(ch)) candidates.push(ch)
      }
    }
    // 如果有多个音节，也显示前几个音节的候选字组合
    if (segments.length > 1) {
      for (const seg of segments) {
        for (const ch of seg.chars.slice(0, 3)) {
          if (!candidates.includes(ch)) candidates.push(ch)
        }
      }
    }
  }

  // 2. 字典精确匹配（全拼匹配已有的词组）
  if (FULL_DICT[lower]) {
    for (const word of FULL_DICT[lower]) {
      if (!candidates.includes(word)) candidates.push(word)
    }
  }

  // 3. 前缀匹配（当前输入可能是某个长词的开始）
  if (candidates.length < 5) {
    for (const key of Object.keys(FULL_DICT)) {
      if (key.startsWith(lower) && key !== lower) {
        for (const word of FULL_DICT[key]) {
          if (!candidates.includes(word)) {
            candidates.push(word)
            if (candidates.length >= 9) break
          }
        }
      }
      if (candidates.length >= 9) break
    }
  }

  // 4. 如果仍无候选，尝试模糊匹配（前缀匹配任意key）
  if (candidates.length === 0) {
    for (const key of Object.keys(FULL_DICT)) {
      if (key.startsWith(lower.slice(0, 2))) {
        for (const word of FULL_DICT[key]) {
          if (!candidates.includes(word)) {
            candidates.push(word)
            if (candidates.length >= 9) break
          }
        }
      }
      if (candidates.length >= 9) break
    }
  }

  return candidates.slice(0, 9)
}

// 提交拼音缓冲（将当前缓冲转为文字）
function commitPinyinBuffer() {
  if (!pinyinBuffer.value) return
  const lower = pinyinBuffer.value.toLowerCase()
  // 尝试分词转换
  const segments = segmentPinyin(lower)
  if (segments.length > 0) {
    inputText.value += segments.map(s => s.chars[0]).join('')
  } else {
    // 无法分词，直接输出拼音原文
    inputText.value += lower
  }
  pinyinBuffer.value = ''
  candidates.value = []
  candidateIndex.value = -1
}

// 选择候选词（智能分段消费：只消耗已选字对应的拼音部分）
function selectCandidate(word) {
  if (!word || !pinyinBuffer.value) return

  const lower = pinyinBuffer.value.toLowerCase()
  const segments = segmentPinyin(lower)

  // 确定该候选词消耗了多少拼音
  let consumedLen = 0

  if (segments.length > 0) {
    // 策略1：单字候选 → 检查属于哪个音节
    if (word.length === 1 && segments[0].chars.includes(word)) {
      // 属于第一个音节，只消耗第一个音节
      consumedLen = segments[0].pinyin.length
    }
    // 策略2：多字候选 → 逐个音节匹配字数
    else if (word.length > 1 && word.length <= segments.length) {
      // 检查是否恰好匹配前 N 个音节的各取一字
      let allMatch = true
      for (let i = 0; i < word.length; i++) {
        if (!segments[i] || !segments[i].chars.includes(word[i])) {
          allMatch = false
          break
        }
      }
      if (allMatch) {
        consumedLen = segments.slice(0, word.length).reduce((sum, s) => sum + s.pinyin.length, 0)
      }
    }

    // 策略3：在完整词典中查找该词对应的拼音前缀
    if (consumedLen === 0) {
      for (let n = segments.length; n >= 1; n--) {
        const combined = segments.slice(0, n).map(s => s.pinyin).join('')
        if (FULL_DICT[combined] && FULL_DICT[combined].includes(word)) {
          consumedLen = combined.length
          break
        }
      }
    }

    // 兜底：如果仍未匹配，消耗第一个音节
    if (consumedLen === 0 && segments.length > 0) {
      consumedLen = segments[0].pinyin.length
    }
  }

  // 如果分段失败，全量消费
  if (consumedLen === 0) {
    consumedLen = lower.length
  }

  // 加入输入框
  inputText.value += word

  // 移除已消费的拼音，保留剩余部分继续选词
  pinyinBuffer.value = lower.slice(consumedLen)

  // 更新候选词列表
  if (pinyinBuffer.value) {
    candidates.value = getCandidates(pinyinBuffer.value)
  } else {
    candidates.value = []
  }
  candidateIndex.value = -1
}

// 清空拼音输入（只清空，不把内容添加到输入框）
function clearPinyin() {
  if (pinyinBuffer.value) {
    pinyinBuffer.value = ''
    candidates.value = []
    candidateIndex.value = -1
  }
}

// 切换输入法模式
function toggleInputMode() {
  // 切换前先提交当前拼音缓冲
  commitPinyinBuffer()
  inputMode.value = inputMode.value === 'en' ? 'cn' : 'en'
  // 切换回字母键盘
  keyboardMode.value = 'qwerty'
  isSymbolMode.value = false
}

function inputKey(key) {
  // 如果在符号键盘模式下，直接输入
  if (keyboardMode.value === 'symbol') {
    commitPinyinBuffer()
    inputText.value += key
    return
  }

  if (inputMode.value === 'cn') {
    // ---- 中文拼音模式 ----
    if (/^[a-zA-Z]$/.test(key)) {
      // 字母键：添加到拼音缓冲
      pinyinBuffer.value += key.toLowerCase()
      candidates.value = getCandidates(pinyinBuffer.value)
      candidateIndex.value = -1
    } else if (key === ' ') {
      // 空格键：提交当前拼音缓冲并添加空格
      commitPinyinBuffer()
      inputText.value += ' '
    } else if (/^\d$/.test(key)) {
      // 数字键：优先尝试候选词选择（按 1-9 选词）
      const idx = parseInt(key) - 1
      if (candidates.value.length > 0 && idx >= 0 && idx < candidates.value.length) {
        selectCandidate(candidates.value[idx])
      } else {
        commitPinyinBuffer()
        inputText.value += key
      }
    } else {
      // 其他键（标点等）：先提交拼音缓冲再直接输入
      commitPinyinBuffer()
      inputText.value += key
    }
  } else {
    // ---- 英文模式 ----
    if (/^[a-zA-Z]$/.test(key)) {
      if (isShifted.value) {
        inputText.value += key.toUpperCase()
        isShifted.value = false
      } else {
        inputText.value += key.toLowerCase()
      }
    } else {
      // 数字、空格、标点：直接输入（Shift 不影响非字母键）
      if (isShifted.value) {
        isShifted.value = false
      }
      inputText.value += key
    }
  }
}

function handleBackspace() {
  // 优先删除拼音缓冲中的字符
  if (pinyinBuffer.value.length > 0) {
    pinyinBuffer.value = pinyinBuffer.value.slice(0, -1)
    if (pinyinBuffer.value.length > 0) {
      candidates.value = getCandidates(pinyinBuffer.value)
    } else {
      candidates.value = []
    }
    candidateIndex.value = -1
  } else {
    // 拼音缓冲为空，删除输入框最后一个字符
    inputText.value = inputText.value.slice(0, -1)
  }
}

function handleShift() {
  isShifted.value = !isShifted.value
}

function toggleSymbols() {
  // 切换到标点符号键盘模式
  keyboardMode.value = keyboardMode.value === 'qwerty' ? 'symbol' : 'qwerty'
  isSymbolMode.value = keyboardMode.value === 'symbol'
}

function handleEnter() {
  // 先提交当前拼音缓冲
  commitPinyinBuffer()
  if (inputText.value.trim()) {
    sendMessage()
  }
  showKeyboard.value = false
}

// 点击输入框时自动显示键盘
function focusInput() {
  showKeyboard.value = true
}

// 景点背景样式（不再依赖图片，使用渐变+水印背景）
const spotBgStyle = computed(() => ({
  background: `linear-gradient(135deg, #0f2018 0%, #1a3a28 30%, #0d2a1a 60%, #162e20 100%)`
}))

// 头发样式（根据发型变化）
const currentHairStyle = computed(() => {
  const color = currentOutfit.value.hairColor
  const style = currentOutfit.value.hairStyle
  const base = {
    background: `linear-gradient(180deg, ${color} 0%, ${adjustColor(color, -20)} 100%)`,
  }
  if (style === 'bun') {
    return { ...base }
  }
  return base
})

// 迷你角色预览样式
const miniCharStyle = computed(() => ({
  '--hair-color': currentOutfit.value.hairColor,
}))

// 工具函数：调整颜色亮度
function adjustColor(hex, amount) {
  const num = parseInt(hex.replace('#', ''), 16)
  const r = Math.min(255, Math.max(0, (num >> 16) + amount))
  const g = Math.min(255, Math.max(0, ((num >> 8) & 0xff) + amount))
  const b = Math.min(255, Math.max(0, (num & 0xff) + amount))
  return '#' + ((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)
}

// 计时器
let timeTimer = null
let idleTimer = null
let blinkTimer = null
let sadtalkerPollTimer = null
let mediaRecorder = null
let audioChunks = []

onMounted(async () => {
  updateTime()
  timeTimer = setInterval(updateTime, 1000)
  startBlinking()
  checkConnection()
  resetIdle()
  // 手机端自动展开聊天面板
  if (window.innerWidth <= 768) {
    chatPanelVisible.value = true
  }
  // 加载外部词典
  loadDictionary()
  // 恢复游客登录状态
  restoreTouristSession()
  // 获取景点数据
  await fetchSpots()
  // 获取百度地图配置（异步，不阻塞）
  fetchBaiduConfig()
  // 获取天气数据（30分钟刷新一次）
  fetchWeather()
  weatherTimer = setInterval(fetchWeather, 30 * 60 * 1000)
  // 初始化人物位置（默认在前景中央偏上，漫画风下移更多）
  charX.value = 50
  const initType = currentAvatarType.value
  if (initType === 'live2d') {
    charY.value = 88  // 漫画风下移约30%（配合0.5缩放，视觉上更深）
  } else if (initType === 'chibi') {
    charY.value = 80
  } else {
    charY.value = 80  // GPU版默认
  }
  baseAvatarScale.value = avatarScaleMap[initType] || 1.0
  charScale.value = calculateScale(charY.value)
  // 初始场景分析（无图片，传景点名）
  setTimeout(() => { analyzeScene('') }, 500)
  // 获取 SadTalker 开关状态（每15秒轮询，支持热更新）
  async function refreshSadTalkerConfig() {
    try {
      const resp = await fetch('/api/chat/config/sadtalker')
      if (resp.ok) {
        const data = await resp.json()
        const prev = sadtalkerEnabled.value
        // 云服务器无GPU时强制禁用视频生成（后端已在 /config/sadtalker 返回 video_generation_enabled）
        if (data.video_generation_enabled === false) {
          sadtalkerEnabled.value = false
          console.log('[Kiosk] 云服务器无GPU模式，视频生成已禁用')
        } else {
          sadtalkerEnabled.value = data.sadtalker_enabled !== false
        }
        // 同步形象类型（优先 active_avatar_type，支持 chibi/live2d/wav2lip/sadtalker）
        const avatarType = data.engine_config?.active_avatar_type || data.engine
        if (avatarType && avatarType !== currentAvatarType.value) {
          console.log('[Kiosk] 形象切换:', currentAvatarType.value, '→', avatarType)
          currentAvatarType.value = avatarType
          baseAvatarScale.value = avatarScaleMap[avatarType] || 1.0
          // 切换时重设默认位置
          if (avatarType === 'live2d') {
            charY.value = 88
          } else if (avatarType === 'chibi') {
            charY.value = 80
          } else {
            charY.value = 80
          }
          charScale.value = calculateScale(charY.value)
          // 只有视频引擎才需要加载待机视频
          if (['sadtalker', 'musetalk', 'wav2lip'].includes(avatarType)) {
            await fetchIdleVideos()
            initIdleDoubleBuffer()
          }
        }
        // 按当前形象类型匹配对应的 avatar 配置（优先使用 all_avatars，fallback 到顶层字段）
        const currentType = currentAvatarType.value
        const allAvatars = data.all_avatars || []
        let matchedAvatar = null
        // 1) 优先按 engine_config.active_avatar_type 匹配
        for (const a of allAvatars) {
          const ecType = a.engine_config?.active_avatar_type
          if (ecType === currentType) { matchedAvatar = a; break }
        }
        // 2) 其次按 engine 字段匹配（适用于数字人引擎）
        if (!matchedAvatar) {
          for (const a of allAvatars) {
            if (a.engine === currentType) { matchedAvatar = a; break }
          }
        }
        // 3) 兜底：按 id 约定 (1=live2d漫画风, 2=chibiQ版, 3=sadtalker数字人)
        if (!matchedAvatar) {
          const idMap = { live2d: 1, chibi: 2 }
          const targetId = idMap[currentType]
          if (targetId) matchedAvatar = allAvatars.find(a => a.id === targetId)
        }
        if (matchedAvatar) {
          if (matchedAvatar.welcome_text) welcomeText.value = matchedAvatar.welcome_text
          if (matchedAvatar.name) avatarName.value = matchedAvatar.name
          if (matchedAvatar.image_url) currentAvatarUrl.value = matchedAvatar.image_url
          // 从 engine_config 加载装扮配置
          const ec = matchedAvatar.engine_config || {}
          if (currentType === 'chibi' && ec.chibiOutfit) {
            currentOutfit.value = { ...currentOutfit.value, ...ec.chibiOutfit }
          }
          if (currentType === 'live2d' && ec.live2dOutfit) {
            live2dOutfit.value = { ...live2dOutfit.value, ...ec.live2dOutfit }
          }
        } else {
          // fallback: 使用顶层字段（兼容旧后端或无匹配场景）
          if (data.welcome_text) {
            welcomeText.value = data.welcome_text
          }
          if (data.avatar_name) {
            avatarName.value = data.avatar_name
          }
          if (data.image_url) {
            currentAvatarUrl.value = data.image_url
          }
        }
        if (prev !== sadtalkerEnabled.value) {
          console.log('[Kiosk] SadTalker开关变更:', prev, '→', sadtalkerEnabled.value)
        }
        // 同步引擎手动开关状态
        if (data.engine_switches) {
          for (const eng of ['wav2lip', 'musetalk', 'sadtalker']) {
            engineEnabledMap.value[eng] = data.engine_switches[eng] !== false
          }
        }
      }
      // 获取引擎基础照片（待机视频缺失时降级使用）
      try {
        const photoResp = await fetch('/api/admin/avatar/engine-base-photos')
        if (photoResp.ok) {
          const photos = await photoResp.json()
          const eng = currentAvatarType.value
          if (photos[eng]?.exists) {
            engineBasePhotoUrl.value = photos[eng].url
          }
        }
      } catch (e) {
        console.warn('[Kiosk] 获取引擎基础照片失败:', e)
      }
    } catch (e) {
      console.warn('[Kiosk] 获取SadTalker配置失败:', e)
    }
    // 标记配置已加载
    if (!configLoaded.value) {
      configLoaded.value = true
      if (pendingGreet.value && !hasGreeted.value) {
        console.log('[Kiosk] 配置就绪，播放迟到的开场视频')
        pendingGreet.value = false
        autoGreet()
      }
    }
  }

  // 获取当前数字人头像 URL（换装后刷新用）
  // 注: refreshSadTalkerConfig 已包含 image_url 加载，此处保留独立函数供换装流程调用
  async function fetchCurrentAvatar() {
    await refreshSadTalkerConfig()
  }

  // 获取预生成的待机视频列表（支持多引擎，根据当前引擎返回对应视频）
  async function fetchIdleVideos() {
    try {
      const engine = currentAvatarType.value || 'wav2lip'
      const resp = await fetch(`/api/admin/avatar/idle-videos?engine=${engine}`)
      if (resp.ok) {
        const data = await resp.json()
        if (data.videos && data.videos.length > 0) {
          idleVideoList.value = data.videos
          console.log('[Kiosk] 待机视频列表已加载:', data.videos.length, '个 (引擎:', data.engine || engine, ')')
        }
      }
    } catch (e) {
      console.warn('[Kiosk] 获取待机视频列表失败:', e)
    }
  }
  await refreshSadTalkerConfig()
  sadtalkerPollTimer = setInterval(refreshSadTalkerConfig, 5000)  // 5秒轮询，及时响应后台配置变更

  // 加载待机视频列表（但不立即播放，等开场视频结束后再播）
  await fetchCurrentAvatar()
  await fetchIdleVideos()
  // 初始化双缓冲：A槽加载第一个待机视频，B槽预加载第二个
  initIdleDoubleBuffer()
  // 不立即播放开场视频，等用户首次触摸屏幕后再播放
  // （浏览器自动播放策略要求用户交互后才能有声播放）
})

onUnmounted(() => {
  clearInterval(timeTimer)
  clearInterval(blinkTimer)
  clearInterval(sadtalkerPollTimer)
  clearInterval(weatherTimer)
  clearTimeout(idleTimer)
  clearTimeout(greetTimer)
  clearTimeout(videoLoadTimer)
  // 停止正在播放的音频
  if (currentAudio.value) {
    try { currentAudio.value.pause() } catch(e) {}
    if (currentAudio.value._blobUrl) {
      URL.revokeObjectURL(currentAudio.value._blobUrl)
    }
    currentAudio.value = null
  }
})

function updateTime() {
  const now = new Date()
  currentTime.value = now.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  currentDate.value = now.toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
}

function startBlinking() {
  blinkTimer = setInterval(() => {
    isBlinking.value = true
    setTimeout(() => { isBlinking.value = false }, 150)
  }, 3000)
}

async function checkConnection() {
  try {
    const resp = await fetch('/api/health')
    isConnected.value = resp.ok
  } catch {
    isConnected.value = false
  }
}

// 获取景点数据
async function fetchWeather() {
  try {
    const resp = await fetch('/api/scenic/weather')
    if (resp.ok) {
      const data = await resp.json()
      weatherData.value = data
      if (data.current) {
        weather.value = {
          temp: data.current.temp,
          desc: data.current.weather_text,
          icon: data.current.weather_icon,
        }
      }
    }
  } catch (_) {
    // 天气获取失败，保持默认显示
  }
}

async function fetchSpots() {
  try {
    const resp = await fetch('/api/scenic/spots')
    if (resp.ok) {
      const result = await resp.json()
      if (result.spots?.length) {
        const mapSize = { width: 420, height: 780 }
        nearbySpots.value = result.spots.map((s, i) => {
          // 查找硬编码景点数据（按名匹配，用于2D地图布局和展示文案）
          const hardcoded = LINGSHAN_SPOTS.find(ls => ls.name === s.name)
          // 从GPS坐标计算2D地图坐标（仅作回退）
          const svgCoords = (s.latitude && s.longitude)
            ? gpsToMap2D(s.longitude, s.latitude, LINGSHAN_BOUNDS, mapSize)
            : { mapX: 200, mapY: 100 + i * 40 }
          return {
            id: s.id,
            name: s.name,
            // 优先用硬编码数据（展示文案/图标/2D坐标），API仅提供GPS和images
            icon: hardcoded?.icon || s.icon || '🏔️',
            description: hardcoded?.description || s.description || '',
            openTime: hardcoded?.openTime || s.open_time || '全天',
            price: hardcoded?.price || s.price || '免费',
            distance: hardcoded?.distance || s.distance || Math.round(100 + i * 80 + Math.random() * 50),
            location: hardcoded?.location || s.location || '',
            category: hardcoded?.category || s.category || '',
            image: (() => {
              let imgs = s.images
              if (typeof imgs === 'string' && imgs.startsWith('[')) {
                try { imgs = JSON.parse(imgs) } catch (_) { imgs = null }
              }
              const url = Array.isArray(imgs) ? imgs[0] : null
              return url || hardcoded?.image || ''
            })(),
            // GPS坐标从API取（Phase 1已修正数据库）
            lat: s.latitude,
            lng: s.longitude,
            // 2D坐标优先用艺术布局，GPS计算值仅作回退
            mapX: hardcoded?.mapX ?? svgCoords.mapX,
            mapY: hardcoded?.mapY ?? svgCoords.mapY
          }
        })
      }
    }
  } catch (e) {
    console.error('获取景点数据失败，使用默认数据:', e)
  }
}

// 获取百度地图等公开配置
async function fetchBaiduConfig() {
  try {
    const resp = await fetch('/api/config/public')
    if (resp.ok) {
      const config = await resp.json()
      if (config.baidu_map_ak) {
        baiduMapsAk.value = config.baidu_map_ak
        console.log('[百度地图] AK已加载')
      } else {
        console.warn('[百度地图] AK未配置，实景地图将不可用')
      }
    }
  } catch (e) {
    console.warn('获取地图配置失败:', e)
  }
}

function dismissAudioHint() {
  showAudioHint.value = false
  clearTimeout(audioHintTimer)
}

function resetIdle() {
  // 检查是否从息屏状态唤醒
  const wasIdle = isIdle.value

  isIdle.value = false
  clearTimeout(idleTimer)

  // 记录用户交互，浏览器自动播放策略要求用户先与页面交互
  if (!userInteracted.value) {
    userInteracted.value = true
    // 尝试取消静音当前正在播放的视频
    if (sadtalkerVideoRef.value && sadtalkerVideoRef.value.muted) {
      try { sadtalkerVideoRef.value.muted = false } catch (e) {}
    }
    // 首次交互：播放开场视频（此时用户已交互，浏览器允许有声播放）
    if (!hasGreeted.value) {
      // 等待配置加载完成再确定用哪个引擎
      if (!configLoaded.value) {
        console.log('[首次交互] 配置未加载，等待加载完成后播放开场视频')
        pendingGreet.value = true
        return
      }
      console.log('[首次交互] 播放开场视频')
      autoGreet()
      return
    }
  }

  // 如果是从息屏状态唤醒，清空聊天记录 + 播放开场视频
  if (wasIdle) {
    console.log('[息屏唤醒] 清空聊天记录并播放开场视频')
    // 清空历史聊天记录
    messages.value = []
    // 重新初始化待机视频双缓冲（防止浏览器在息屏期间卸载了视频）
    initIdleDoubleBuffer()
    // 重置开场标志，允许播放开场视频
    hasGreeted.value = false
    autoGreet()
    return
  }

  idleTimer = setTimeout(() => {
    // AI 正在思考或数字人正在播放时，不进入待机，重新计时
    if (isLoading.value || isTalking.value) {
      resetIdle()
      return
    }
    isIdle.value = true
  }, 300000)  // 5分钟无对话后进入息屏
}

// 欢迎语音 timer ID，用于卸载时清理
let greetTimer = null

/**
 * 生成并播放开场对话视频（文本 → TTS → SadTalker视频）
 */
async function generateOpeningVideo(text) {
  if (!text || hasGreeted.value) return

  isTalking.value = true
  sadtalkerPhase.value = 'generating'  // 待机视频继续播放，遮罩层显示"正在生成"
  currentSubtitle.value = '正在生成开场视频...'

  try {
    // 调用 /generate-opening API（通过 Vite 代理到 8001 端口）
    const formData = new FormData()
    formData.append('text', text)
    formData.append('voice', 'zh-CN-XiaoxiaoNeural')

    const resp = await fetch('/generate-opening', {
      method: 'POST',
      body: formData
    })

    if (!resp.ok) {
      const errText = await resp.text()
      throw new Error(`生成失败: ${errText}`)
    }

    const data = await resp.json()
    if (data.success) {
      console.log('[开场视频] ✅ 生成成功:', data.video_url)
      // 播放生成的视频（playSadTalkerVideo 不切 phase，等 loadedmetadata 再切）
      await playSadTalkerVideo(data.video_url)
    } else {
      throw new Error('生成失败: 返回状态异常')
    }
  } catch (e) {
    console.error('[开场视频] ❌ 生成失败:', e)
    sadtalkerPhase.value = 'idle'
    // 降级方案：使用原来的音频播放
    console.warn('[开场视频] 降级为音频播放')
    await speak(text)
  }
}

async function autoGreet() {
  if (hasGreeted.value) return
  hasGreeted.value = true

  // 将欢迎语作为开场对话气泡加入聊天框
  const greetText = welcomeText.value || `您好！欢迎来到灵山胜境，我是AI导览助手${avatarName.value || '小灵'}，请问有什么可以帮您？`
  messages.value.push({
    id: Date.now(),
    role: 'assistant',
    content: greetText,
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })
  await scrollToBottom()

  if (isVideoEngine.value) {
    // 数字人模式：优先从待机视频列表中找到实际的开场视频文件名（API返回的是正确的UUID文件名）
    // 如果待机视频列表还没加载（首次启动时 fetchIdleVideos 可能还没完成），先加载
    if (!idleVideoList.value || idleVideoList.value.length === 0) {
      console.log('[开场视频] 待机视频列表未加载，先获取...')
      try {
        const engine = currentAvatarType.value || 'wav2lip'
        const resp = await fetch(`/api/admin/avatar/idle-videos?engine=${engine}`)
        if (resp.ok) {
          const data = await resp.json()
          if (data.videos && data.videos.length > 0) {
            idleVideoList.value = data.videos
            console.log('[开场视频] 待机视频列表已加载:', data.videos.length, '个 (引擎:', data.engine || engine, ')')
          }
        }
      } catch (e) {
        console.warn('[开场视频] 获取待机视频列表失败:', e)
      }
    }
    let openingVideoUrl = null
    const idleList = (idleVideoList.value || []).filter(v => {
      const url = typeof v === 'string' ? v : (v.url || '')
      return url && url.includes('opening')
    })
    if (idleList.length > 0) {
      const first = idleList[0]
      openingVideoUrl = typeof first === 'string' ? first : first.url
      console.log('[开场视频] 从 API 列表找到开场视频:', openingVideoUrl)
    } else if (sadtalkerEnabled.value) {
      // GPU 模式保底：用强缓存破坏参数请求 /opening.mp4（防止浏览器用旧缓存）
      openingVideoUrl = `${getEngineVideoPrefix()}/opening.mp4?nocache=${Date.now()}`
      console.warn('[开场视频] 未从 API 找到开场视频，使用保底路径:', openingVideoUrl)
    }
    // 无 GPU 模式且无预生成开场视频 → 降级 TTS；GPU 模式也无视频时同样降级
    if (openingVideoUrl) {
      console.log('[开场视频] 播放:', openingVideoUrl)
      console.log('[开场视频]   本机文件:', urlToFilePath(openingVideoUrl))
      isOpeningPlaying.value = true
      playSadTalkerVideo(openingVideoUrl)
      // wav2lip 视频不含音轨，同步播放 TTS 语音
      if (currentAvatarType.value === 'wav2lip') {
        console.log('[开场视频] wav2lip 无音轨，同步播放 TTS')
        speak(greetText)
      }
      // 注意：isOpeningPlaying 在 onVideoEnded / onVideoError / 用户中断时清除
    } else {
      console.log('[开场视频] 无可用开场视频，降级为 TTS 语音')
      sadtalkerPhase.value = 'idle'
      await speak(greetText)
    }
  } else {
    // Q版/漫画风：降级用 TTS 音频播放欢迎语
    console.log('[开场语音] TTS 模式播放欢迎语')
    await speak(greetText)
  }
}

/**
 * 播放 SadTalker 生成的数字人视频
 */
function playSadTalkerVideo(url) {
  if (!url) return
  clearTimeout(videoLoadTimer)
  // 规范化 URL：去掉各种可能的 localhost/127.0.0.1 前缀，保留纯路径
  let videoPath = url
  videoPath = videoPath.replace(/^https?:\/\/localhost:8001/, '')
  videoPath = videoPath.replace(/^https?:\/\/127\.0\.0\.1:8001/, '')
  videoPath = videoPath.replace(/^https?:\/\/localhost:8016/, '')
  if (videoPath && !videoPath.startsWith('/')) {
    videoPath = '/' + videoPath
  }
  console.log('[SadTalker] playSadTalkerVideo:', videoPath)
  console.log('[SadTalker]   本机文件:', urlToFilePath(videoPath))
  avatarVideoUrl.value = videoPath
  sadtalkerPhase.value = 'speaking'
  currentSubtitle.value = '数字人讲解中...'
  isTalking.value = true
  // 显示音频提示，5秒后自动消失
  showAudioHint.value = true
  clearTimeout(audioHintTimer)
  audioHintTimer = setTimeout(() => { showAudioHint.value = false }, 5000)

  // 兜底：nextTick 后如果视频还没开始播放（canplay 可能因缓存命中而丢失），手动触发
  nextTick(() => {
    const videoEl = sadtalkerVideoRef.value
    if (videoEl && videoEl.paused && videoEl.src && sadtalkerPhase.value === 'speaking') {
      console.log('[SadTalker] nextTick 兜底播放（视频尚未开始）')
      if (!userInteracted.value) videoEl.muted = true
      videoEl.play().catch(() => {})  // 失败也无妨，onVideoCanPlay 会处理
    }
  })

  // 超时兜底
  videoLoadTimer = setTimeout(() => {
    if (sadtalkerPhase.value === 'speaking' && avatarVideoUrl.value === videoPath) {
      console.warn('[SadTalker] 视频加载超时，回退到 idle')
      isOpeningPlaying.value = false
      avatarVideoUrl.value = ''
      sadtalkerPhase.value = 'idle'
      isTalking.value = false
      currentSubtitle.value = ''
    }
  }, 8000)
}

// 视频加载超时兜底
let videoLoadTimer = null
// 音频提示自动消失定时器
let audioHintTimer = null

// 视频播放时的绝对地址日志
function onVideoPlayLog(label, event) {
  const videoEl = event.target
  const src = videoEl?.src || videoEl?.currentSrc || '(unknown)'
  console.log(`[Video] ▶ ${label} 开始播放`)
  console.log(`[Video]   网络URL: ${src}`)
  // 映射到本机文件绝对路径
  const filePath = urlToFilePath(src)
  console.log(`[Video]   本机文件: ${filePath}`)
}

// URL → 本地文件绝对路径映射
function urlToFilePath(url) {
  // 去掉协议和域名
  let path = url.replace(/^https?:\/\/[^/]+/, '')
  // 去掉 ?t=xxx 缓存参数
  path = path.split('?')[0]

  const PROJECT_ROOT = 'D:\\TalkingV2'

  const mappings = [
    { prefix: '/sadtalker-videos/',  local: PROJECT_ROOT + '\\sadtalker-service\\output\\' },
    { prefix: '/musetalk-videos/',   local: PROJECT_ROOT + '\\musetalk-service\\output\\' },
    { prefix: '/wav2lip-videos/',    local: PROJECT_ROOT + '\\wav2lip-service\\output\\' },
    { prefix: '/sadtalker-avatars/', local: PROJECT_ROOT + '\\sadtalker-service\\avatars\\' },
    { prefix: '/musetalk-avatars/',  local: PROJECT_ROOT + '\\musetalk-service\\avatars\\' },
    { prefix: '/wav2lip-avatars/',   local: PROJECT_ROOT + '\\wav2lip-service\\avatars\\' },
    { prefix: '/dialogue-videos/',   local: PROJECT_ROOT + '\\scenic-guide-ai\\backend\\app\\videos\\dialogue\\' },
    { prefix: '/static/avatar/',     local: PROJECT_ROOT + '\\scenic-guide-ai\\backend\\static\\avatar\\' },
    { prefix: '/spot-images/',       local: PROJECT_ROOT + '\\图片\\' },
  ]

  for (const m of mappings) {
    if (path.startsWith(m.prefix)) {
      return m.local + path.substring(m.prefix.length).replace(/\//g, '\\')
    }
  }

  // 未匹配映射：显示原始路径
  return '(unknown mapping) ' + path.replace(/\//g, '\\')
}

// 视频可以播放时的回调
function onVideoCanPlay(e) {
  clearTimeout(videoLoadTimer)
  const videoEl = e.target
  console.log('[SadTalker] 视频就绪:', videoEl.videoWidth, 'x', videoEl.videoHeight, '时长:', videoEl.duration.toFixed(1), 's')
  // 先尝试有声播放，被浏览器拒绝再静音回退
  // 不要上来就 muted=true，避免开场白永远没声音
  if (userInteracted.value) {
    videoEl.muted = false
  } else {
    // 用户还没交互过，先静音尝试（浏览器自动播放策略要求）
    videoEl.muted = true
  }
  const playPromise = videoEl.play()
  if (playPromise !== undefined) {
    playPromise.then(() => {
      console.log('[SadTalker] 视频播放成功, muted:', videoEl.muted)
      // 播放成功有声音了，提前关闭提示
      if (!videoEl.muted) {
        dismissAudioHint()
      }
      // 播放成功后，如果有用户交互，确保没有静音
      if (userInteracted.value && videoEl.muted) {
        try { videoEl.muted = false } catch (e) {}
      }
    }).catch(err => {
      console.warn('[SadTalker] 视频播放失败:', err.name, err.message)
      if (err.name === 'NotAllowedError') {
        // 浏览器拒绝有声播放，静音重试
        videoEl.muted = true
        videoEl.play().then(() => {
          console.log('[SadTalker] 静音重试播放成功，等待用户交互后取消静音')
          // 显示音频提示引导用户点击人物
          showAudioHint.value = true
          // 注册一次性点击监听，用户交互后立即取消静音
          const unmuteOnInteract = () => {
            if (videoEl.muted) {
              videoEl.muted = false
              console.log('[SadTalker] 用户交互，取消静音')
            }
            showAudioHint.value = false
            document.removeEventListener('click', unmuteOnInteract)
            document.removeEventListener('touchstart', unmuteOnInteract)
          }
          document.addEventListener('click', unmuteOnInteract)
          document.addEventListener('touchstart', unmuteOnInteract)
        }).catch(err2 => {
          console.warn('[SadTalker] 静音重试仍失败:', err2.name)
          isOpeningPlaying.value = false
          sadtalkerPhase.value = 'idle'
        })
      } else {
        isOpeningPlaying.value = false
        sadtalkerPhase.value = 'idle'
      }
    })
  }
}

// 视频加载错误回调
function onVideoError(e) {
  clearTimeout(videoLoadTimer)
  console.error('[SadTalker] 视频加载错误:', e.target.error?.message || '未知错误')
  showAudioHint.value = false
  clearTimeout(audioHintTimer)
  isOpeningPlaying.value = false
  avatarVideoUrl.value = ''
  sadtalkerPhase.value = 'idle'
  isTalking.value = false
}

// 视频播放结束回调
function onVideoEnded() {
  console.log('[SadTalker] 视频播放结束:', avatarVideoUrl.value)

  showAudioHint.value = false
  clearTimeout(audioHintTimer)
  isOpeningPlaying.value = false
  isTalking.value = false
  currentSubtitle.value = ''

  const videoUrl = avatarVideoUrl.value
  avatarVideoUrl.value = ''
  sadtalkerPhase.value = 'idle'

  // 对话视频由后端管理缓存（最多2个），前端不再单独删除
  // 对话视频路径: /dialogue-videos/dialogue_*.mp4
  // 待机/开场视频路径: /sadtalker-videos/*.mp4
  if (videoUrl && videoUrl.includes('/dialogue-videos/')) {
    console.log('[SadTalker] 对话视频播放完毕，由后端管理缓存清理:', videoUrl)
  }

  // 切回 idle：确保待机视频正在播放
  resetIdle()
  // 防御：如果待机视频因任何原因暂停了，重新播放
  nextTick(() => {
    const v = idleVideoRef.value
    if (v && v.paused) {
      console.log('[Video] 待机视频已暂停，重新播放')
      v.muted = true
      v.play().catch(err => console.warn('[Video] 待机视频恢复播放失败:', err.name))
    }
  })
}

// ========== 待机视频逻辑（单视频循环播放） ==========

// 选取待机视频（排除开场白、欢迎、对话视频，仅选 idle 类型）
function pickRandomIdleVideo(excludeUrl) {
  // 优先用 API 返回的 video_type 字段筛选
  let list = (idleVideoList.value || []).filter(v => {
    const url = typeof v === 'string' ? v : (v.url || '')
    // 如果有 video_type 字段，直接用
    if (v.video_type === 'idle') return url ? true : false
    // 兜底：排除 opening/welcome/greeting/dialogue
    return url && !url.includes('opening') && !url.includes('welcome') && !url.includes('greeting') && !url.includes('dialogue')
  })
  // Wav2Lip / MuseTalk 可能只有 opening 视频 → 回退到任意可用视频（不要显示静态图）
  if (list.length === 0) {
    list = (idleVideoList.value || []).filter(v => {
      const url = typeof v === 'string' ? v : (v.url || '')
      return !!url
    })
    if (list.length > 0) {
      console.log('[Video] 无纯 idle 视频，回退到可用视频列表:', list.length, '个')
    }
  }
  if (list.length === 0) return null
  // 排除指定 URL
  const candidates = list.filter(v => {
    const url = typeof v === 'string' ? v : v.url
    return url !== excludeUrl
  })
  const pick = candidates.length > 0 ? candidates : list
  const chosen = pick[Math.floor(Math.random() * pick.length)]
  return typeof chosen === 'string' ? chosen : chosen.url
}

// 初始化待机视频：选取一个并设置 loop 循环播放
function initIdleDoubleBuffer() {
  const first = pickRandomIdleVideo(null)
  console.log('[Video] 🎬 initIdleVideo, 待机视频:', first)
  console.log('[Video]   本机文件:', first ? urlToFilePath(first) : '(null)')
  if (!first) {
    console.warn('[Video] ⚠ 没有可用的待机视频！idleVideoList:', idleVideoList.value.map(v => typeof v === 'string' ? v : v.url))
    idleVideoSrc.value = ''
    return
  }
  idleVideoSrc.value = first
  // 确保视频开始播放（autoplay + 手动 play 双保险）
  nextTick(() => {
    const v = idleVideoRef.value
    if (v) {
      v.muted = true
      const playPromise = v.play()
      if (playPromise !== undefined) {
        playPromise.catch(err => {
          console.warn('[Video] 待机视频 play 失败:', err.name, err.message)
          // 静音重试
          v.muted = true
          setTimeout(() => v.play().catch(() => {}), 300)
        })
      }
    }
  })
}

// 待机视频播完一轮的回调（loop 正常时不会触发，兜底用）
function onIdleVideoEnded() {
  console.log('[Video] 待机视频 ended 事件触发，重新播放')
  const v = idleVideoRef.value
  if (v) {
    v.currentTime = 0
    v.play().catch(() => {})
  }
}

// 待机视频加载错误的回调
function onIdleVideoError(e) {
  console.error('[Video] 待机视频加载错误:', e.target?.error?.message || '未知错误')
  // 清空当前 URL 让 fallback 图片显示
  idleVideoSrc.value = ''
}


async function speak(text) {
  currentSubtitle.value = text
  isTalking.value = true
  // 停止之前正在播放的音频
  if (currentAudio.value) {
    try { currentAudio.value.pause() } catch(e) {}
    if (currentAudio.value._blobUrl) {
      URL.revokeObjectURL(currentAudio.value._blobUrl)
    }
    currentAudio.value = null
  }
  try {
    const resp = await fetch('/api/voice/tts', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, voice: 'zh-CN-XiaoxiaoNeural', speed: 1.0 })
    })
    if (resp.ok) {
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const audio = new Audio(url)
      audio._blobUrl = url
      currentAudio.value = audio
      await audio.play()
      audio.onended = () => {
        isTalking.value = false
        currentSubtitle.value = ''
        URL.revokeObjectURL(url)
        currentAudio.value = null
        resetIdle()
      }
    } else {
      isTalking.value = false
      currentSubtitle.value = ''
      resetIdle()
    }
  } catch {
    setTimeout(() => {
      isTalking.value = false
      currentSubtitle.value = ''
      resetIdle()
    }, Math.min(text.length * 150, 5000))
  }
}

// 直接播放后端返回的 TTS 音频 URL（省资源模式，不发二次TTS请求）
function playAudioUrl(url, subtitle) {
  if (!url) return
  currentSubtitle.value = subtitle || ''
  isTalking.value = true
  if (currentAudio.value) {
    try { currentAudio.value.pause() } catch(e) {}
    currentAudio.value = null
  }
  const audio = new Audio(url)
  currentAudio.value = audio
  audio.play().catch(() => {})
  audio.onended = () => {
    isTalking.value = false
    currentSubtitle.value = ''
    currentAudio.value = null
    resetIdle()
  }
  audio.onerror = () => {
    isTalking.value = false
    currentSubtitle.value = ''
    currentAudio.value = null
    resetIdle()
  }
}

async function sendMessage() {
  if (!inputText.value.trim() || isLoading.value) return
  const text = inputText.value.trim()
  inputText.value = ''
  showKeyboard.value = false
  pinyinBuffer.value = ''
  candidates.value = []
  await processQuery(text)
}

async function askQuick(q) {
  if (isLoading.value) return  // 防止连续点击导致并发请求
  await processQuery(q)
}

async function processQuery(text) {
  const msgId = Date.now()
  messages.value.push({
    id: msgId,
    role: 'user',
    content: text,
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })
  await scrollToBottom()
  isLoading.value = true

  // 创建中止控制器
  const controller = new AbortController()
  abortController.value = controller

  try {
    // 如果开场视频正在播放，强行打断（用户在开场白未播完时提问）
    const isOpening = isOpeningPlaying.value || (avatarVideoUrl.value && avatarVideoUrl.value.includes('opening'))
    if (isOpening) {
      console.log('[中断开场] 用户在开场视频播放期间提问，强行打断')
      clearTimeout(videoLoadTimer)
      if (sadtalkerVideoRef.value) {
        try { sadtalkerVideoRef.value.pause() } catch (e) {}
      }
      avatarVideoUrl.value = ''
      sadtalkerPhase.value = 'idle'
      isTalking.value = false
      currentSubtitle.value = ''
      isOpeningPlaying.value = false
      hasGreeted.value = true  // 确保不会再次触发开场
    }

    // 两套逻辑：视频引擎开启→视频对话 / 关闭→纯TTS语音
    const useVideoEngine = isVideoEngine.value && sadtalkerEnabled.value

    // 切到思考状态
    if (isVideoEngine.value) {
      sadtalkerPhase.value = useVideoEngine ? 'thinking' : 'idle'
    }

    // 根据开关调用不同端点
    const endpoint = useVideoEngine ? '/api/chat/message' : '/api/chat/message-tts'
    const sid = store.sessionId || 'kiosk_default'
    const body = useVideoEngine
      ? {
          message: text,
          session_id: sid,
          platform: 'kiosk',
          context: { spot: currentSpot.value, mode: 'kiosk' },
          generate_video: true,
          generate_audio: true
        }
      : {
          message: text,
          session_id: sid,
          platform: 'kiosk'
        }

    console.log('[AI] 使用端点:', endpoint, 'VideoEngine:', useVideoEngine, 'engine:', currentAvatarType.value)
    const resp = await fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
      signal: controller.signal
    })

    let answer = ''
    let videoUrl = ''
    let audioUrl = ''
    if (resp.ok) {
      const data = await resp.json()
      answer = data.answer || '抱歉，我没有找到相关信息。'
      videoUrl = data.video_url || ''
      audioUrl = data.audio_url || ''
      console.log('[AI] 响应 — videoUrl:', videoUrl, 'audioUrl:', audioUrl)

      if (useVideoEngine && videoUrl) {
        // 视频引擎模式：播放对话视频
        playSadTalkerVideo(videoUrl)
      } else if (!useVideoEngine && audioUrl) {
        // 省资源模式：直接播放后端返回的 TTS 音频（不发起二次 TTS 请求）
        playAudioUrl(audioUrl, answer)
        if (isVideoEngine.value) {
          sadtalkerPhase.value = 'idle'
        }
      } else if (useVideoEngine && !videoUrl) {
        // 视频引擎模式但视频生成失败，降级用 TTS
        await speak(answer)
        sadtalkerPhase.value = 'idle'
      } else {
        // 非视频引擎模式且后端未返回audio_url，兜底调用TTS
        await speak(answer)
        if (isVideoEngine.value) {
          sadtalkerPhase.value = 'idle'
        }
      }
    } else {
      answer = '系统繁忙，请稍后再试。'
    }

    messages.value.push({
      id: Date.now(),
      role: 'assistant',
      content: answer,
      time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    })
    await scrollToBottom()
  } catch (err) {
    // 区分用户主动中断和网络错误
    if (err.name === 'AbortError') {
      // 用户主动中止，不显示错误
      console.log('[AI] 用户主动中断对话')
    } else {
      console.error('[AI] processQuery 出错:', err)
      if (isVideoEngine.value) {
        sadtalkerPhase.value = 'idle'
      }
      messages.value.push({
        id: Date.now(),
        role: 'assistant',
        content: '网络连接异常，请检查网络后重试。',
        time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
      })
    }
  } finally {
    abortController.value = null
    isLoading.value = false
    resetIdle()  // AI 结束工作，重置待机计时器，给用户留时间阅读
  }
}

async function startVoice() {
  if (isRecording.value || isLoading.value) return
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioChunks = []
    mediaRecorder = new MediaRecorder(stream)
    mediaRecorder.ondataavailable = e => audioChunks.push(e.data)
    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      const blob = new Blob(audioChunks, { type: 'audio/webm' })
      await transcribeAudio(blob)
    }
    mediaRecorder.start()
    isRecording.value = true
    voiceStatus.value = '正在录音，请说话...'
  } catch {
    voiceStatus.value = '麦克风权限被拒绝'
    setTimeout(() => { voiceStatus.value = '' }, 2000)
  }
}

function stopVoice() {
  if (!isRecording.value || !mediaRecorder) return
  isRecording.value = false
  voiceStatus.value = '正在识别语音...'
  mediaRecorder.stop()
}

async function transcribeAudio(blob) {
  try {
    voiceStatus.value = '正在识别语音，请稍候...'
    const formData = new FormData()
    formData.append('audio', blob, 'recording.webm')
    formData.append('language', 'zh')
    
    console.log('开始语音识别，上传音频大小:', blob.size, '字节')
    const resp = await fetch('/api/voice/transcribe', { 
      method: 'POST', 
      body: formData 
    })
    
    if (resp.ok) {
      const data = await resp.json()
      voiceStatus.value = ''
      console.log('识别结果:', data)
      if (data.text) {
        inputText.value = data.text
        // 语音识别后仅填入输入框，由用户确认后手动点击发送
        voiceStatus.value = '识别完成，请确认后发送'
        setTimeout(() => { voiceStatus.value = '' }, 3000)
      } else {
        voiceStatus.value = '未能识别到语音内容，请重试'
        setTimeout(() => { voiceStatus.value = '' }, 3000)
      }
    } else {
      const errorText = await resp.text()
      console.error('语音识别失败:', resp.status, errorText)
      voiceStatus.value = '语音识别失败: ' + (errorText || resp.statusText)
      setTimeout(() => { voiceStatus.value = '' }, 3000)
    }
  } catch (err) {
    console.error('语音识别异常:', err)
    voiceStatus.value = '语音服务异常: ' + err.message
    setTimeout(() => { voiceStatus.value = '' }, 3000)
  }
}

// ========== 2D人物移动和位置控制 ==========

// 角色基础缩放比例（用于景深缩放计算）
const baseAvatarScale = ref(1.0)

/**
 * 计算缩放值（固定，不随Y坐标变化）
 */
function calculateScale(y) {
  return baseAvatarScale.value * 0.85
}

/**
 * 缓动函数 - easeOutCubic
 */
function easeOutCubic(t) {
  return 1 - Math.pow(1 - t, 3)
}

/**
 * 移动人物到指定位置
 */
function moveCharacterTo(newX, newY, duration = 800) {
  if (isMoving.value) {
    // 如果正在移动，取消当前动画
    if (moveAnimationId) {
      cancelAnimationFrame(moveAnimationId)
    }
  }

  const startX = charX.value
  const startY = charY.value

  targetX.value = newX
  targetY.value = newY
  isMoving.value = true

  const startTime = performance.now()

  function animate(currentTime) {
    const elapsed = currentTime - startTime
    const progress = Math.min(elapsed / duration, 1)
    const eased = easeOutCubic(progress)

    // 只插值位置，不改变缩放
    charX.value = startX + (newX - startX) * eased
    charY.value = startY + (newY - startY) * eased

    if (progress < 1) {
      moveAnimationId = requestAnimationFrame(animate)
    } else {
      // 动画结束
      charX.value = newX
      charY.value = newY
      isMoving.value = false
      moveAnimationId = null
    }
  }

  moveAnimationId = requestAnimationFrame(animate)
}

/**
 * 点击背景区域移动人物
 */
function onSceneClick(event) {
  // 如果正在加载中，不响应点击（但换装面板和对话时仍可移动）
  if (isLoading.value) return
  // 视频引擎数字人不随点击移动
  if (isVideoEngine.value) return

  const container = event.currentTarget
  const rect = container.getBoundingClientRect()

  // 计算点击位置相对于容器的百分比
  const clickX = ((event.clientX - rect.left) / rect.width) * 100
  const clickY = ((event.clientY - rect.top) / rect.height) * 100

  // 限制移动范围（避免太靠边）
  const clampedX = Math.max(15, Math.min(85, clickX))
  const clampedY = Math.max(depthConfig.value.minY, Math.min(depthConfig.value.maxY, clickY))

  // 全方位平移，不改变人物大小
  moveCharacterTo(clampedX, clampedY, 1000)
}

/**
 * 分析场景图片，获取路径信息
 */
async function analyzeScene(imageUrl) {
  try {
    // 如果是本地图片，先上传分析
    if (imageUrl && !imageUrl.startsWith('data:')) {
      const resp = await fetch('/api/scene/simple-analyze', {
        method: 'POST',
        headers: {},
      })
      
      if (resp.ok) {
        const data = await resp.json()
        scenePaths.value = data.paths || []
        sceneObstacles.value = data.obstacles || []
        depthConfig.value.minY = data.depth_range?.min_y || 35
        depthConfig.value.maxY = data.depth_range?.max_y || 90
        
        if (data.default_position) {
          defaultPosition.value = data.default_position
          charX.value = data.default_position.x
          charY.value = data.default_position.y
          charScale.value = calculateScale(charY.value)
        }
        console.log('场景分析完成:', data)
      }
    }
  } catch (err) {
    console.error('场景分析失败:', err)
    // 使用默认配置
    depthConfig.value = {
      minY: 35,
      maxY: 95,
      minScale: 0.6,
      maxScale: 1.3
    }
  }
}

function selectSpot(spot) {
  selectedSpot.value = spot
  spotImageFailed.value = false  // 重置图片加载状态
  showSpotDetail.value = true
  currentSpot.value = spot.name
  store.setSpot(spot.name)

  // 分析新场景（无图片，传空串）
  analyzeScene('')

  // 加载景点评论
  fetchSpotReviews(spot.id)
}

function applyOutfit(outfit) {
  currentOutfit.value = { ...outfit }
}

function applyLive2dOutfit(outfit) {
  live2dOutfit.value = { ...outfit }
}

// ===== 游客登录/注册 =====
async function handleLogin() {
  if (!loginPhone.value.trim() || !loginPassword.value.trim()) return
  try {
    const formBody = new URLSearchParams({ username: loginPhone.value, password: loginPassword.value })
    const res = await fetch('/api/tourist/auth/login', {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body: formBody
    })
    const data = await res.json()
    if (res.ok) {
      touristUser.value = { tourist_id: data.tourist_id, nickname: data.nickname }
      localStorage.setItem('tourist_token', data.access_token)
      localStorage.setItem('tourist_info', JSON.stringify({ tourist_id: data.tourist_id, nickname: data.nickname }))
      showTouristLogin.value = false
    } else {
      alert(data.detail || '登录失败')
    }
  } catch (e) { alert('网络错误') }
}

async function handleRegister() {
  if (!regPhone.value.trim() || !regPassword.value.trim()) return
  try {
    const res = await fetch('/api/tourist/auth/register', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone: regPhone.value, password: regPassword.value, nickname: regNickname.value || undefined })
    })
    const data = await res.json()
    if (res.ok) {
      touristUser.value = { tourist_id: data.tourist_id, nickname: data.nickname }
      localStorage.setItem('tourist_token', data.access_token)
      localStorage.setItem('tourist_info', JSON.stringify({ tourist_id: data.tourist_id, nickname: data.nickname }))
      showTouristLogin.value = false
      isRegisterMode.value = false
    } else {
      alert(data.detail || '注册失败')
    }
  } catch (e) { alert('网络错误') }
}

// 游客登出
function handleTouristLogout() {
  touristUser.value = null
  showTouristProfile.value = false
  localStorage.removeItem('tourist_token')
  localStorage.removeItem('tourist_info')
}

// 恢复登录状态
function restoreTouristSession() {
  const token = localStorage.getItem('tourist_token')
  const info = localStorage.getItem('tourist_info')
  if (token && info) {
    try { touristUser.value = JSON.parse(info) } catch (e) {}
  }
}

// ===== 投诉建议 =====
async function submitComplaint() {
  if (!complaintTitle.value.trim() || !complaintContent.value.trim()) return
  complaintSubmitting.value = true
  try {
    const token = localStorage.getItem('tourist_token') || ''
    const res = await fetch('/api/tourist/complaints', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: JSON.stringify({
        type: complaintType.value,
        category: complaintCategory.value,
        title: complaintTitle.value,
        content: complaintContent.value,
        contact: complaintContact.value || undefined,
      })
    })
    const data = await res.json()
    if (res.ok) {
      alert(data.message || '提交成功')
      showComplaintDialog.value = false
      complaintTitle.value = ''
      complaintContent.value = ''
      complaintContact.value = ''
    } else {
      alert(data.detail || '提交失败')
    }
  } catch (e) { alert('网络错误') }
  finally { complaintSubmitting.value = false }
}

// ===== 景点评论 =====
async function fetchSpotReviews(spotId) {
  try {
    const res = await fetch(`/api/tourist/spots/${spotId}/reviews?page=1&size=50`)
    const data = await res.json()
    if (res.ok) {
      spotReviews.value = data.items || []
      spotReviewAvg.value = data.avg_rating || 0
      spotReviewTotal.value = data.total || 0
      // 检查当前用户是否已评论
      userHasReviewed.value = false
      if (touristUser.value) {
        userHasReviewed.value = spotReviews.value.some(r => r.tourist_id === touristUser.value.tourist_id)
      }
      reviewRating.value = 0
      reviewContent.value = ''
    }
  } catch (e) { console.error('加载评论失败', e) }
}

async function submitReview() {
  if (!touristUser.value || !selectedSpot.value || reviewRating.value === 0) return
  try {
    const token = localStorage.getItem('tourist_token')
    const res = await fetch(`/api/tourist/spots/${selectedSpot.value.id}/reviews`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ spot_id: selectedSpot.value.id, rating: reviewRating.value, content: reviewContent.value })
    })
    const data = await res.json()
    if (res.ok) {
      alert('评论成功！')
      fetchSpotReviews(selectedSpot.value.id)
    } else {
      alert(data.detail || '评论失败')
    }
  } catch (e) { alert('网络错误') }
}

function formatReviewTime(t) {
  if (!t) return ''
  return t.replace('T', ' ').substring(0, 16)
}

function selectOutfit(preset) {
  currentOutfit.value = { ...preset }
  showOutfitPanel.value = false
}

async function startGuide(spot) {
  currentSpot.value = spot.name
  showSpotDetail.value = false
  spotPanelVisible.value = false
  chatPanelVisible.value = true
  await processQuery('请介绍一下' + spot.name + '的历史文化和特色看点')
}

function abortGeneration() {
  if (!abortController.value) return

  // 调用后端取消 API（后端会根据当前引擎路由到正确的服务）
  const sid = store.sessionId || 'kiosk_default'
  fetch(`/api/chat/cancel/${encodeURIComponent(sid)}`, { method: 'POST' }).catch(() => {})

  // 额外直接调用引擎取消接口（双保险），根据当前引擎类型路由
  const ENGINE_CANCEL_URLS = { sadtalker: 'http://localhost:8001', musetalk: 'http://localhost:8003', wav2lip: 'http://localhost:8004' }
  const engineBaseUrl = ENGINE_CANCEL_URLS[currentAvatarType.value] || 'http://localhost:8001'
  fetch(`${engineBaseUrl}/cancel/${encodeURIComponent(sid)}`, { method: 'POST' }).catch(() => {})

  // 中止网络请求
  abortController.value.abort()
  abortController.value = null

  // 停止当前音频
  if (currentAudio.value) {
    try { currentAudio.value.pause() } catch(e) {}
    if (currentAudio.value._blobUrl) {
      URL.revokeObjectURL(currentAudio.value._blobUrl)
    }
    currentAudio.value = null
  }

  // 停止数字人视频
  if (sadtalkerVideoRef.value) {
    try { sadtalkerVideoRef.value.pause() } catch(e) {}
  }
  if (isVideoEngine.value) {
    sadtalkerPhase.value = 'idle'
  }

  // 停止 TTS 语音
  window.speechSynthesis?.cancel()

  // 对话提示
  messages.value.push({
    id: Date.now(),
    role: 'system',
    content: 'AI对话已被中断',
    time: new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  })

  isLoading.value = false
  isTalking.value = false
  isOpeningPlaying.value = false
  clearTimeout(videoLoadTimer)
  resetIdle()
}

function clearChat() {
  messages.value = []
}

async function scrollToBottom() {
  await nextTick()
  if (chatMessages.value) {
    chatMessages.value.scrollTop = chatMessages.value.scrollHeight
  }
}
</script>

<style scoped>
* { box-sizing: border-box; margin: 0; padding: 0; }

.kiosk-container {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #0a1628 0%, #1a2a4a 40%, #0d2137 100%);
  color: #fff;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
  user-select: none;
}

/* ========== 顶部栏 ========== */
.kiosk-header {
  height: 80px;
  /* 不透明玻璃效果 */
  background: rgba(15, 25, 45, 0.98);
  border-bottom: 1px solid rgba(255,255,255,0.15);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 32px; flex-shrink: 0;
  z-index: 10;
}
.header-left { display: flex; align-items: center; gap: 16px; }
.logo { width: 48px; height: 48px; border-radius: 8px; }
.scenic-name { font-size: 22px; font-weight: 700; color: #fff; }
.current-spot { font-size: 14px; color: rgba(255,255,255,0.6); margin-top: 2px; display: block; }
.status-bar {
  display: flex; align-items: center; gap: 8px;
  background: rgba(255,255,255,0.08); padding: 8px 16px; border-radius: 20px; font-size: 14px;
}
.status-dot {
  width: 8px; height: 8px; border-radius: 50%;
  background: #666; transition: background 0.3s;
}
.status-dot.active { background: #4ade80; box-shadow: 0 0 8px #4ade80; }
.header-right { display: flex; align-items: center; gap: 24px; text-align: right; }
.time { font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; }
.date { font-size: 12px; color: rgba(255,255,255,0.6); }
.weather { display: flex; align-items: center; gap: 6px; font-size: 18px; cursor: pointer; }

/* ========== 主内容 ========== */
.kiosk-main {
  flex: 1; display: flex;
  overflow: visible;
  /* height: 0 让 flex 容器高度完全由 flex:1 分配决定，不受子内容撑开 */
  height: 0;
}

/* ========== 中间景区+数字人区 ========== */
.avatar-section {
  flex: 1;
  width: 100%;
  position: relative;
  display: flex; flex-direction: column;
  padding: 24px; gap: 16px;
  border-right: 1px solid rgba(255,255,255,0.08);
  /* 改为 visible，防止人物底部被裁切；人物超出时自动撑开 */
  overflow: visible;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
/* 聊天面板展开时，数字人区域收缩 */
.avatar-section.chat-open {
  flex: 1;
  border-right: 2px solid rgba(59,130,246,0.5);
}
/* 景点面板展开时，数字人区域收缩 */
.avatar-section.spot-open {
  flex: 1;
  border-left: 2px solid rgba(34,197,94,0.5);
}
/* 两边同时展开 */
.avatar-section.chat-open.spot-open {
  flex: 1;
}

/* 景区背景图 */
.spot-bg {
  position: absolute; inset: 0;
  border-radius: 20px;
  cursor: pointer;
  overflow: hidden;
}
/* 隐隐约约的灵山水印 */
.spot-bg::after {
  content: '灵山';
  position: absolute;
  top: 50%; left: 50%;
  transform: translate(-50%, -50%) rotate(-30deg);
  font-size: 200px;
  font-weight: 900;
  color: rgba(255,255,255,0.035);
  pointer-events: none;
  font-family: 'Microsoft YaHei', 'PingFang SC', serif;
  white-space: nowrap;
}
.spot-bg-overlay {
  position: absolute; inset: 0; border-radius: 20px;
  background: linear-gradient(
    to bottom,
    rgba(10,22,40,0.15) 0%,
    rgba(10,22,40,0.45) 40%,
    rgba(10,22,40,0.85) 100%
  );
}

/* 路径提示层 */
.path-hints {
  position: absolute; inset: 0;
  pointer-events: none;
}
.path-hint {
  position: absolute;
  background: rgba(74, 222, 128, 0.15);
  border: 1px dashed rgba(74, 222, 128, 0.4);
  border-radius: 8px;
}

/* 换装按钮 - 景区右上角 */
.outfit-btn {
  position: absolute;
  top: 36px;
  right: 36px;
  width: 50px; height: 50px;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.25);
  border-radius: 14px;
  cursor: pointer; font-size: 26px;
  display: flex; align-items: center; justify-content: center;
  backdrop-filter: blur(8px);
  transition: all 0.2s;
  z-index: 50;
  flex-shrink: 0;
}
.outfit-btn:hover {
  background: rgba(255,255,255,0.22);
  border-color: rgba(255,255,255,0.4);
  transform: scale(1.08);
  box-shadow: 0 4px 16px rgba(0,0,0,0.3);
}

/* 换装面板 */
.outfit-panel {
  position: absolute;
  top: 90px; right: 24px;
  width: 280px;
  max-height: 90vh;
  background: rgba(10,20,45,0.95);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255,255,255,0.15);
  border-radius: 18px;
  padding: 16px;
  z-index: 60;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  overflow-y: auto;
  overflow-x: hidden;
}
/* 滚动条样式 */
.outfit-panel::-webkit-scrollbar {
  width: 4px;
}
.outfit-panel::-webkit-scrollbar-track {
  background: rgba(255,255,255,0.05);
  border-radius: 2px;
}
.outfit-panel::-webkit-scrollbar-thumb {
  background: rgba(255,255,255,0.2);
  border-radius: 2px;
}
.outfit-panel::-webkit-scrollbar-thumb:hover {
  background: rgba(255,255,255,0.3);
}
.outfit-panel-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 12px; padding-bottom: 10px;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}
.outfit-panel-title { font-size: 15px; font-weight: 600; color: #fff; }
.outfit-close {
  background: rgba(255,255,255,0.1); border: none; color: rgba(255,255,255,0.6);
  width: 26px; height: 26px; border-radius: 50%; cursor: pointer; font-size: 13px;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.outfit-close:hover { background: rgba(255,255,255,0.2); color: #fff; }

/* AI 数字人换装 */
.ai-avatar-section {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.1);
}
.ai-avatar-controls {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ai-prompt-input {
  width: 100%;
  padding: 10px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.2);
  background: rgba(255,255,255,0.08);
  color: #fff;
  font-size: 13px;
  resize: vertical;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.ai-prompt-input:focus {
  border-color: #00d4ff;
}
.ai-prompt-input::placeholder {
  color: rgba(255,255,255,0.35);
}
/* 文件上传样式 */
.ai-file-input {
  width: 100%;
  padding: 8px;
  border-radius: 8px;
  border: 1px dashed rgba(0,212,255,0.5);
  background: rgba(0,212,255,0.05);
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  outline: none;
}
.ai-file-input:hover {
  border-color: #00d4ff;
  background: rgba(0,212,255,0.1);
}
.ai-file-input::file-selector-button {
  margin-right: 10px;
  padding: 4px 12px;
  border: none;
  border-radius: 4px;
  background: #00d4ff;
  color: #1a1a2e;
  font-size: 12px;
  cursor: pointer;
}
.file-name {
  font-size: 12px;
  color: rgba(255,255,255,0.7);
  padding: 4px 0;
}
.ai-options {
  display: flex;
  gap: 16px;
}
.gender-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: rgba(255,255,255,0.8);
  cursor: pointer;
}
.gender-label input[type="radio"] {
  accent-color: #00d4ff;
}
.ai-generate-btn {
  padding: 10px 16px;
  border-radius: 8px;
  border: 1px solid rgba(0,212,255,0.4);
  background: rgba(0,212,255,0.15);
  color: #00d4ff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.ai-generate-btn:hover:not(:disabled) {
  background: rgba(0,212,255,0.25);
  border-color: rgba(0,212,255,0.6);
}
.ai-generate-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.ai-avatar-preview {
  margin-top: 12px;
  padding: 12px;
  background: rgba(255,255,255,0.05);
  border-radius: 12px;
  border: 1px solid rgba(255,255,255,0.1);
}
.preview-img {
  width: 100%;
  border-radius: 8px;
  background: #000;
}
.preview-actions {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}
.confirm-btn {
  flex: 1;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(46,204,113,0.4);
  background: rgba(46,204,113,0.15);
  color: #2ecc71;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.confirm-btn:hover {
  background: rgba(46,204,113,0.25);
}
.regenerate-btn {
  flex: 1;
  padding: 8px 12px;
  border-radius: 8px;
  border: 1px solid rgba(255,255,255,0.2);
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.8);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}
.regenerate-btn:hover {
  background: rgba(255,255,255,0.15);
}
.generation-progress {
  margin-top: 10px;
}
.progress-text {
  font-size: 12px;
  color: rgba(255,255,255,0.6);
  margin-bottom: 6px;
}
.progress-bar {
  height: 4px;
  background: rgba(255,255,255,0.1);
  border-radius: 2px;
  overflow: hidden;
}
.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #00d4ff, #2ecc71);
  border-radius: 2px;
  transition: width 0.3s ease;
}

/* 角色预览 */
.outfit-preview {
  display: flex; justify-content: center;
  padding: 8px 0 14px;
}
.preview-char {
  transform: scale(0.55);
  transform-origin: center top;
}
/* 漫画风预览区 - 只展示头部 */
.live2d-preview {
  height: 180px;
  overflow: hidden;
  position: relative;
  border-radius: 12px;
  background: linear-gradient(180deg, #e8d5ff 0%, #f5e6ff 100%);
}
.live2d-preview :deep(.anime-wrapper) {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  height: 100%;
  padding-top: 0;
}
.live2d-preview :deep(.anime-char) {
  transform: scale(1.1) !important;
  transform-origin: center top !important;
  margin-top: 400px;
}
.mini-chibi {
  display: flex; flex-direction: column; align-items: center;
  position: relative; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
}
.mini-hair {
  width: 72px; height: 40px;
  background: var(--hair-color, #3d2000);
  border-radius: 36px 36px 10px 10px;
  position: relative; z-index: 1;
  display: flex; align-items: flex-start; justify-content: center;
  margin-bottom: -5px; /* 头发紧贴头部 */
}
/* 发饰 */
.mini-hair-deco {
  position: absolute; top: 2px; right: 2px;
  font-size: 14px; z-index: 2;
}
.mini-head {
  width: 60px; height: 60px;
  background: linear-gradient(180deg, #ffe0c8, #ffd4b0);
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  margin-top: -5px; position: relative; z-index: 2;
}
.mini-face { position: relative; width: 40px; height: 36px; }
.mini-eye {
  position: absolute; top: 8px; width: 12px; height: 14px;
  background: #3d2000; border-radius: 50%;
}
.mini-eye.left { left: 2px; }
.mini-eye.right { right: 2px; }
/* 眼睛高光 */
.mini-eye::after {
  content: ''; position: absolute; top: 2px; left: 2px;
  width: 5px; height: 5px; background: #fff; border-radius: 50%;
}
.mini-blush {
  position: absolute; bottom: 8px; width: 10px; height: 6px;
  background: rgba(255,100,100,0.35); border-radius: 50%; filter: blur(1px);
}
.mini-blush.left { left: 0; }
.mini-blush.right { right: 0; }
.mini-mouth {
  position: absolute; bottom: 3px; left: 50%; transform: translateX(-50%);
  width: 10px; height: 0;
  border-bottom: 2px solid #d4846a; border-radius: 0 0 50% 50%;
}
.mini-body {
  width: 50px; height: 38px;
  border-radius: 10px 10px 16px 16px;
  display: flex; align-items: flex-start; justify-content: center;
  margin-top: -2px; position: relative; z-index: 1;
}
.mini-collar {
  width: 20px; height: 8px;
  border-radius: 0 0 10px 10px;
  margin-top: 0;
}
.mini-arm {
  position: absolute;
  width: 16px; height: 32px;
  border-radius: 8px;
  /* 手臂要在身体前面 */
  /* mini-chibi 结构: 头发40px + 头60px = 100px，身体从100px开始 */
  z-index: 2;
  top: 95px; /* 与肩膀同一高度 */
}
.mini-arm.left {
  left: 0; /* 向内靠拢 */
  transform-origin: top center;
  animation: waveLeft 4s ease-in-out infinite;
}
.mini-arm.right {
  right: 0; /* 向内靠拢 */
  transform-origin: top center;
  animation: waveRight 4s ease-in-out infinite 0.5s;
}
/* 迷你手 - 和主页面角色的手样式完全一致 */
.mini-hand {
  position: absolute;
  bottom: -7px; left: 50%; transform: translateX(-50%);
  width: 14px; height: 14px;
  background: linear-gradient(180deg, #ffe0c8, #ffd4b0);
  border-radius: 50%;
  z-index: 1;
}

/* 漫画风迷你预览 */
.mini-anime {
  display: flex; flex-direction: column; align-items: center;
  position: relative; filter: drop-shadow(0 4px 8px rgba(0,0,0,0.3));
}
.mini-a-hair {
  width: 80px; height: 100px;
  border-radius: 40px 40px 20px 20px;
  position: relative; z-index: 1;
}
.mini-a-head {
  width: 70px; height: 80px;
  background: linear-gradient(180deg, #ffe0cc, #ffd4b0);
  border-radius: 50% 50% 45% 45%;
  margin-top: -10px; position: relative; z-index: 2;
}
.mini-a-body {
  width: 70px; height: 65px;
  border-radius: 15px 15px 0 0;
  margin-top: -5px; position: relative; z-index: 1;
}
.mini-a-skirt {
  width: 80px; height: 45px;
  border-radius: 0 0 40px 40px;
  margin-top: -2px; z-index: 1;
}

/* 换装分组 */
.outfit-group {
  margin-bottom: 12px;
}
.group-label {
  font-size: 12px; color: rgba(255,255,255,0.5);
  margin-bottom: 8px; padding-left: 2px;
}
.group-options {
  display: flex; flex-wrap: wrap; gap: 6px;
}
.option-chip {
  padding: 5px 12px;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 20px; cursor: pointer; color: rgba(255,255,255,0.8);
  font-size: 13px; transition: all 0.2s;
}
.option-chip:hover { background: rgba(255,255,255,0.12); color: #fff; }
.option-chip.active {
  background: rgba(96,165,250,0.2);
  border-color: rgba(96,165,250,0.6);
  color: #93c5fd;
}
.deco-chip { font-size: 12px; }

/* ========== 数字人舞台 ========== */
/* 人物现在可以自由定位，不再使用flex布局 */
.avatar-stage-inner {
  position: absolute;
  display: flex; flex-direction: column; align-items: center;
  z-index: 2;
  /* left, top, transform 由内联样式控制 */
  /* 防止切换时人物被裁切 */
  will-change: transform, opacity;
  /* 切换动画 */
  transition: transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1), opacity 0.2s ease;
  /* 缩放锚点在胸口位置 */
  transform-origin: center 65%;
}

/* 思考状态动画 */
.chibi.thinking { animation: thinkingBob 1.2s ease-in-out infinite; }
.chibi.thinking .chibi-head { animation: thinkingTilt 2s ease-in-out infinite; }
@keyframes thinkingBob {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
@keyframes thinkingTilt {
  0%, 100% { transform: rotate(0deg); }
  25% { transform: rotate(-3deg); }
  75% { transform: rotate(3deg); }
}
.chibi.talking .chibi-mouth {
  animation: talkAnim 0.2s infinite alternate;
}
@keyframes talkAnim {
  from { height: 5px; width: 18px; }
  to { height: 13px; width: 26px; }
}

/* 思考气泡（已移除全局气泡，各角色组件内部自行管理） */

/* ========== 数字人本体 ========== */
/*
  关键：给 chibi 设置固定宽度（与头部同宽），这样手臂的
  position: absolute 定位就有了可靠的基准，不会随屏幕宽度飘移。
  布局从顶到底：头发(behind) → 头部 → 身体 → 手臂 → 手
*/
.chibi {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  /* 固定宽度 = 头部宽度，作为所有 absolute 定位的基准 */
  width: 100px;
  filter: drop-shadow(0 20px 40px rgba(0,0,0,0.35));
}

/* 头发 - 宽于头部，自然盖住头两侧；在头部之后（z-index低），只露出刘海 */
.chibi-hair {
  width: 120px; height: 65px;
  border-radius: 60px 60px 20px 20px;
  position: relative;
  /* 在头发容器内垂直方向：内容贴着底部（头顶露出来） */
  display: flex; align-items: flex-end; justify-content: center;
  z-index: 1;
  overflow: visible;
  /* 遮住头发与头的接缝 */
}
.hair-deco {
  position: absolute;
  /* 发饰定位在头的右上角（相对于 chibi 容器 = 头中心） */
  top: 12px; right: -2px;
  font-size: 22px; z-index: 5;
  animation: accessoryBounce 2s ease-in-out infinite;
  filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));
}
@keyframes accessoryBounce {
  0%, 100% { transform: translateY(0) rotate(-5deg); }
  50% { transform: translateY(-3px) rotate(5deg); }
}

/* 头部 - 在头发上方（z-index高），头顶刚好从头发底部露出来 */
.chibi-head {
  width: 100px; height: 100px;
  position: relative;
  /* 头部完全盖在头发之上 */
  z-index: 2;
  margin-top: -30px; /* 头顶从头发露出来 */
}
.chibi-face {
  width: 100%; height: 100%;
  background: linear-gradient(180deg, #ffe0c8 0%, #ffd4b0 60%, #ffcb9a 100%);
  border-radius: 50% 50% 48% 48%;
  position: relative;
  box-shadow:
    inset 0 -8px 16px rgba(255,180,120,0.25),
    0 6px 20px rgba(255,180,120,0.25);
  animation: breathe 3s ease-in-out infinite;
}
@keyframes breathe {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
}

/* 眼睛 */
.chibi-eyes {
  position: absolute; top: 30px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 24px;
}
.eye {
  width: 22px; height: 26px;
  background: #3d2000; border-radius: 50%;
  position: relative; overflow: hidden; transition: height 0.1s;
}
.eye.blink { height: 4px; top: 11px; }
.eye-highlight {
  position: absolute; top: 4px; left: 3px;
  width: 10px; height: 10px; background: #fff; border-radius: 50%;
}

/* 腮红 */
.blush {
  position: absolute; bottom: 24px;
  width: 18px; height: 12px;
  background: rgba(255,100,100,0.35);
  border-radius: 50%; filter: blur(2px);
}
.blush.left { left: 8px; }
.blush.right { right: 8px; }

/* 嘴巴 */
.chibi-mouth {
  position: absolute; bottom: 18px; left: 50%; transform: translateX(-50%);
  height: 0; border-bottom: 3px solid #c8604a;
  border-radius: 0 0 50% 50%; overflow: hidden;
  transition: all 0.2s;
}

/* 思考表情 */
.chibi-emotion {
  position: absolute; top: 8px; right: 8px;
}
.emotion-dots {
  font-size: 16px; color: #888; font-weight: bold; letter-spacing: -2px;
  animation: dotsBlink 1s step-end infinite;
}
@keyframes dotsBlink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.2; }
}

/* 身体 */
.chibi-body {
  width: 80px; height: 68px;
  border-radius: 16px 16px 28px 28px;
  position: relative;
  /* 身体在头发和头之后 */
  z-index: 1;
  margin-top: -4px;
  box-shadow: 0 6px 16px rgba(0,0,0,0.2);
  display: flex; align-items: flex-start; justify-content: center;
}
.body-collar {
  width: 30px; height: 12px;
  border-radius: 0 0 15px 15px;
  margin-top: 0; flex-shrink: 0;
}

/* 手臂 - 紧贴身体两侧 */
/* chibi 宽100px，身体居中宽80px，身体高度约70px */
/* 手臂位置：top = 头底部(70px) + 身体往下15px = 身体中段两侧 */
/* z-index: 3 = 盖住身体(1)和头部(2)，露出在身体两侧 */
.chibi-arm {
  position: absolute;
  width: 28px; height: 55px;
  border-radius: 14px;
  z-index: 3;
  /* 从身体中段开始（头70px + 身体往下25px = 身体中段） */
  top: 125px;
  transform-origin: top center;
}
.chibi-arm.left {
  left: -8px;  /* 向左移出身体 */
  animation: waveLeft 4s ease-in-out infinite;
}
.chibi-arm.right {
  right: -8px; /* 向右移出身体 */
  animation: waveRight 4s ease-in-out infinite 0.5s;
}
@keyframes waveLeft {
  0%, 100% { transform: rotate(-5deg); }
  50% { transform: rotate(5deg); }
}
@keyframes waveRight {
  0%, 100% { transform: rotate(5deg); }
  50% { transform: rotate(-5deg); }
}

/* 手：手臂底部的肤色圆球 */
.arm-hand {
  position: absolute;
  bottom: -8px; left: 50%; transform: translateX(-50%);
  width: 24px; height: 24px;
  background: linear-gradient(180deg, #ffe0c8, #ffd4b0);
  border-radius: 50%;
  z-index: 4;
}

/* 漂浮装饰 */
.chibi-deco {
  position: absolute; pointer-events: none; z-index: 10;
  top: calc(50% - 200px); left: calc(50% - 160px);
  width: 320px;
}
.deco-star {
  position: absolute; font-size: 14px;
  animation: floatStar 3s ease-in-out infinite; opacity: 0.6;
}
.deco-star:nth-child(1) { left: 5%; top: 10px; animation-duration: 2.5s; }
.deco-star:nth-child(2) { right: 5%; top: 0; animation-duration: 3.2s; animation-delay: 0.5s; }
.deco-star:nth-child(3) { left: 0; top: 50px; animation-duration: 2.8s; animation-delay: 1s; }
.deco-star:nth-child(4) { right: 0; top: 45px; animation-duration: 3.5s; animation-delay: 1.5s; }
@keyframes floatStar {
  0%, 100% { transform: translateY(0) rotate(0deg); opacity: 0.6; }
  50% { transform: translateY(-8px) rotate(15deg); opacity: 1; }
}

/* 声波 */
.sound-wave {
  position: absolute; bottom: 24px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: flex-end; gap: 4px; height: 38px; z-index: 5;
}
.sound-wave span {
  width: 4px; background: rgba(74,222,128,0.8); border-radius: 2px;
  animation: soundWave 0.8s ease-in-out infinite alternate;
}
.sound-wave span:nth-child(1) { height: 10px; }
.sound-wave span:nth-child(2) { height: 20px; animation-delay: 0.1s; }
.sound-wave span:nth-child(3) { height: 30px; animation-delay: 0.2s; }
.sound-wave span:nth-child(4) { height: 38px; animation-delay: 0.15s; }
.sound-wave span:nth-child(5) { height: 26px; animation-delay: 0.25s; }
.sound-wave span:nth-child(6) { height: 16px; animation-delay: 0.05s; }
.sound-wave span:nth-child(7) { height: 8px; animation-delay: 0.3s; }
@keyframes soundWave { to { height: 4px; } }

/* 字幕 */
.subtitle-bar {
  min-height: 52px; background: rgba(0,0,0,0.6);
  border-radius: 12px; padding: 10px 20px;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: opacity 0.3s;
  border: 1px solid rgba(255,255,255,0.1);
  position: relative; z-index: 3;
}
.subtitle-bar.visible { opacity: 1; }
.subtitle-text { font-size: 17px; line-height: 1.6; text-align: center; }

/* 快捷景点按钮 */
.spot-shortcuts {
  display: flex; gap: 10px; flex-wrap: wrap; position: relative; z-index: 3;
  margin-top: auto;  /* 靠下对齐 */
}
.spot-btn {
  flex: 1 1 calc(33% - 8px);
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.3);
  border-radius: 12px; padding: 10px 8px;
  color: #fff; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  transition: all 0.2s; font-size: 13px; min-height: 60px;
  text-shadow: 0 1px 3px rgba(0,0,0,0.5);
  backdrop-filter: blur(8px);
}
.spot-btn:hover, .spot-btn:active {
  background: rgba(64,120,255,0.3); border-color: rgba(64,120,255,0.5);
  transform: scale(1.02);
}
.spot-btn.active {
  background: rgba(74,222,128,0.15); border-color: rgba(74,222,128,0.4);
}
.spot-icon { font-size: 22px; }
.spot-name { text-align: center; }

/* ========== 左侧景点面板 ========== */
.spot-section {
  width: 0;
  flex-shrink: 0;
  display: flex; flex-direction: column;
  position: relative;
  overflow: hidden;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.spot-section.expanded {
  width: 50%;
}
.spot-list-panel {
  width: 100%;
  height: 100%;
  display: flex; flex-direction: column;
  background: rgba(10, 14, 30, 0.92);
  backdrop-filter: blur(20px);
  border-right: 2px solid rgba(34,197,94,0.5);
}
.spot-list-header {
  padding: 18px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.08);
  display: flex; align-items: center; justify-content: space-between;
}
.spot-list-header h3 {
  color: #fff; font-size: 18px; margin: 0;
}

/* ===== 视图切换按钮 ===== */
.view-toggle {
  display: flex; gap: 4px;
  background: rgba(255,255,255,0.06);
  border-radius: 8px; padding: 3px;
}
.view-toggle button {
  padding: 5px 12px; border: none; border-radius: 6px;
  background: transparent; color: rgba(255,255,255,0.5);
  font-size: 12px; cursor: pointer; transition: all 0.2s;
}
.view-toggle button.active {
  background: rgba(34,197,94,0.25);
  color: #4ade80; font-weight: 600;
}
.view-toggle button:hover:not(.active) {
  color: rgba(255,255,255,0.8);
}

/* ===== 地图视图容器 ===== */
.spot-map-container {
  flex: 1; display: flex; flex-direction: column;
  overflow: hidden; position: relative;
  background: #020617;
}
/* 2D地图标记和样式完全由 Scenic2DMap.vue (scoped) 管理，此处不再重复 */
.spot-list-scroll {
  flex: 1; overflow-y: auto; padding: 12px;
  display: flex; flex-direction: column; gap: 10px;
}
.spot-list-scroll::-webkit-scrollbar { width: 4px; }
.spot-list-scroll::-webkit-scrollbar-thumb { background: rgba(34,197,94,0.3); border-radius: 4px; }

.spot-list-item {
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 14px;
  padding: 14px 16px;
  display: flex; align-items: flex-start; gap: 12px;
  cursor: pointer;
  transition: all 0.25s;
}
.spot-list-item:hover {
  background: rgba(34,197,94,0.12);
  border-color: rgba(34,197,94,0.35);
  transform: translateX(4px);
}
.spot-list-item.active {
  background: rgba(34,197,94,0.18);
  border-color: rgba(34,197,94,0.5);
  box-shadow: 0 0 12px rgba(34,197,94,0.15);
}
.spot-list-icon {
  font-size: 32px;
  flex-shrink: 0;
  width: 48px; height: 48px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(34,197,94,0.1);
  border-radius: 12px;
}
.spot-list-thumb {
  width: 48px; height: 48px;
  object-fit: cover;
  border-radius: 12px;
  flex-shrink: 0;
}
.spot-list-info {
  flex: 1; display: flex; flex-direction: column; gap: 4px;
  min-width: 0;
}
.spot-list-name {
  font-size: 16px; font-weight: 600; color: #fff;
}
.spot-list-desc {
  font-size: 12px; color: rgba(255,255,255,0.55);
  line-height: 1.4;
  overflow: hidden; text-overflow: ellipsis;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.spot-list-meta {
  display: flex; gap: 10px; font-size: 11px;
  color: rgba(255,255,255,0.45); margin-top: 4px;
}

/* 左侧景点展开按钮（镜像右侧聊天按钮） */
.spot-toggle-btn {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 80px;
  background: linear-gradient(135deg, rgba(34,197,94,0.95), rgba(22,163,74,0.95));
  border: none;
  border-radius: 0 20px 20px 0;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1000;
  box-shadow: 4px 0 20px rgba(34,197,94,0.4);
}
.spot-toggle-btn:hover {
  background: linear-gradient(135deg, rgba(34,197,94,1), rgba(22,163,74,1));
  box-shadow: 6px 0 25px rgba(34,197,94,0.6);
}
.spot-toggle-btn.expanded {
  left: calc(50% - 46px);
  border-radius: 20px 0 0 20px;
}

/* 左侧面板滑入动画 */
.slide-from-left-enter-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-from-left-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-from-left-enter-from {
  opacity: 0;
  transform: translateX(-100%);
}
.slide-from-left-leave-to {
  opacity: 0;
  transform: translateX(-100%);
}

/* ========== 右侧交互区 ========== */
.interaction-section {
  /* 默认隐藏（0宽度），展开时显示50% */
  width: 0;
  flex-shrink: 0;
  display: flex; flex-direction: column; padding: 24px; gap: 16px;
  position: relative;
  overflow: hidden;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
/* 展开时占50%宽度 */
.interaction-section.expanded {
  width: 50%;
  padding: 24px;
}

/* 展开/收起按钮 - 默认在右侧边缘，展开时跟随聊天面板到50%位置 */
.chat-toggle-btn {
  position: fixed;
  /* 默认在右侧边缘（数字人全屏时） */
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 40px;
  height: 80px;
  background: linear-gradient(135deg, rgba(59,130,246,0.95), rgba(29,78,216,0.95));
  border: none;
  border-radius: 20px 0 0 20px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  z-index: 1000;
  box-shadow: -4px 0 20px rgba(59,130,246,0.4);
}
.chat-toggle-btn:hover {
  background: linear-gradient(135deg, rgba(59,130,246,1), rgba(29,78,216,1));
  box-shadow: -6px 0 25px rgba(59,130,246,0.6);
}
/* 展开后，按钮移到50%位置（向右偏移16px，避免遮挡边框） */
.chat-toggle-btn.expanded {
  right: calc(50% - 46px);
  border-radius: 0 20px 20px 0;
}
.toggle-text {
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  writing-mode: vertical-rl;
  text-orientation: mixed;
  letter-spacing: 2px;
}

/* 聊天面板 */
.chat-panel {
  flex: 1;
  min-height: 0;
  background: rgba(255,255,255,0.04);
  border: 1px solid rgba(255,255,255,0.08); border-radius: 16px;
  display: flex; flex-direction: column; overflow: hidden;
}
.chat-header {
  padding: 14px 20px; border-bottom: 1px solid rgba(255,255,255,0.08);
  display: flex; justify-content: space-between; align-items: center;
}
.chat-header h3 { font-size: 16px; font-weight: 600; }
.clear-btn {
  background: none; border: 1px solid rgba(255,255,255,0.2);
  color: rgba(255,255,255,0.6); padding: 4px 12px; border-radius: 6px;
  cursor: pointer; font-size: 13px;
}
.clear-btn:hover { color: #fff; border-color: rgba(255,255,255,0.5); }
.clear-btn:disabled { color: rgba(255,255,255,0.2); border-color: rgba(255,255,255,0.08); cursor: not-allowed; }
.chat-messages {
  flex: 1; overflow-y: auto; padding: 16px;
  display: flex; flex-direction: column; gap: 16px; scroll-behavior: smooth;
}
.chat-messages::-webkit-scrollbar { width: 4px; }
.chat-messages::-webkit-scrollbar-track { background: transparent; }
.chat-messages::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.2); border-radius: 2px; }
.chat-empty {
  text-align: center; color: rgba(255,255,255,0.4);
  padding: 40px 20px; line-height: 2.5;
}
.message { display: flex; gap: 12px; align-items: flex-start; }
.message.user { flex-direction: row-reverse; }
.message-avatar { font-size: 24px; flex-shrink: 0; margin-top: 4px; }
.message-bubble {
  max-width: 85%; padding: 12px 16px; border-radius: 14px; line-height: 1.6;
}
.message.user .message-bubble {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  border-radius: 14px 4px 14px 14px;
}
.message.assistant .message-bubble {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 4px 14px 14px 14px;
}
.message.system {
  justify-content: center;
}
.message.system .message-bubble {
  background: rgba(239, 68, 68, 0.15);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 10px;
  max-width: 70%;
  text-align: center;
}
.message-bubble p { font-size: 15px; }
.message-time { font-size: 11px; color: rgba(255,255,255,0.4); margin-top: 4px; display: block; }
.message-enter-active { transition: all 0.3s; }
.message-enter-from { opacity: 0; transform: translateY(10px); }

/* AI思考中提示 */
.thinking-tip {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 14px;
  background: rgba(251,191,36,0.1); border: 1px solid rgba(251,191,36,0.3);
  border-radius: 10px; color: #fbbf24; font-size: 13px;
  animation: fadeInTip 0.3s ease;
}
@keyframes fadeInTip {
  from { opacity: 0; transform: translateY(-5px); }
  to { opacity: 1; transform: translateY(0); }
}
.thinking-dots { display: flex; gap: 3px; align-items: center; }
.thinking-dots span {
  width: 6px; height: 6px; border-radius: 50%; background: #fbbf24;
  animation: thinkBounce 1s ease-in-out infinite;
}
.thinking-dots span:nth-child(2) { animation-delay: 0.15s; }
.thinking-dots span:nth-child(3) { animation-delay: 0.3s; }

/* 输入区 */
.input-panel {
  background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px; padding: 16px; display: flex; flex-direction: column; gap: 12px;
}
.voice-status {
  display: flex; align-items: center; justify-content: center; gap: 12px;
  color: #4ade80; font-size: 14px; padding: 8px;
  background: rgba(74,222,128,0.1); border-radius: 8px;
}
.voice-wave { display: flex; align-items: center; gap: 3px; height: 20px; }
.voice-wave span {
  width: 3px; background: #4ade80; border-radius: 2px;
  animation: voiceWave 0.6s ease-in-out infinite alternate;
}
.voice-wave span:nth-child(1) { height: 8px; }
.voice-wave span:nth-child(2) { height: 16px; animation-delay: 0.1s; }
.voice-wave span:nth-child(3) { height: 20px; animation-delay: 0.2s; }
.voice-wave span:nth-child(4) { height: 14px; animation-delay: 0.15s; }
.voice-wave span:nth-child(5) { height: 6px; animation-delay: 0.3s; }
@keyframes voiceWave { to { height: 4px; } }

.input-row { display: flex; gap: 8px; }
.text-input {
  flex: 1; background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.15); color: #fff;
  padding: 14px 16px; border-radius: 12px; font-size: 15px; outline: none;
}
.text-input::placeholder { color: rgba(255,255,255,0.35); }
.text-input:focus { border-color: rgba(64,120,255,0.6); background: rgba(255,255,255,0.1); }
.text-input:disabled { opacity: 0.5; cursor: not-allowed; }
.voice-btn {
  width: 52px; height: 52px; border-radius: 12px;
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2);
  color: #fff; font-size: 22px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s; flex-shrink: 0;
}
.voice-btn.recording { background: rgba(239,68,68,0.4); border-color: #ef4444; animation: pulse 1s infinite; }
.voice-btn.disabled { opacity: 0.4; cursor: not-allowed; }
@keyframes pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
.send-btn {
  padding: 0 20px; height: 52px; border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  border: none; color: #fff; font-size: 15px; font-weight: 600;
  cursor: pointer; transition: all 0.2s; white-space: nowrap;
}
.send-btn:hover:not(:disabled) { background: linear-gradient(135deg, #60a5fa, #3b82f6); }
.send-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.abort-btn {
  padding: 0 20px; height: 52px; border-radius: 12px;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  border: none; color: #fff; font-size: 15px; font-weight: 600;
  cursor: pointer; transition: all 0.2s; white-space: nowrap;
  animation: pulse-abort 1.2s infinite;
}
.abort-btn:hover { background: linear-gradient(135deg, #f87171, #ef4444); }
@keyframes pulse-abort {
  0%, 100% { box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.5); }
  50% { box-shadow: 0 0 0 8px rgba(239, 68, 68, 0); }
}

.quick-questions { display: flex; gap: 8px; flex-wrap: wrap; }
.quick-btn {
  background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
  color: rgba(255,255,255,0.8); padding: 7px 14px;
  border-radius: 20px; cursor: pointer; font-size: 13px;
  transition: all 0.2s; white-space: nowrap;
}
.quick-btn:hover, .quick-btn:active {
  background: rgba(64,120,255,0.25); border-color: rgba(64,120,255,0.5); color: #fff;
}

/* 景点详情面板 */
.spot-detail-panel {
  position: fixed; right: 0; top: 80px; bottom: 0; width: 380px;
  background: rgba(10,22,40,0.95); backdrop-filter: blur(20px);
  border-left: 1px solid rgba(255,255,255,0.12);
  padding: 24px; overflow-y: auto; z-index: 100;
}
.close-panel {
  position: absolute; top: 16px; right: 16px;
  background: rgba(255,255,255,0.1); border: none; color: #fff;
  width: 32px; height: 32px; border-radius: 50%; cursor: pointer; font-size: 16px;
}
.spot-detail-panel h2 { font-size: 24px; margin-bottom: 16px; padding-right: 40px; }
.spot-image-wrap {
  border-radius: 12px; margin-bottom: 16px;
  background: rgba(255,255,255,0.05); min-height: 160px;
  display: flex; align-items: center; justify-content: center;
  overflow: hidden;
}
.spot-detail-image {
  width: 100%;
  height: 100%;
  min-height: 200px;
  max-height: 280px;
  object-fit: cover;
  border-radius: 12px;
}
.spot-icon-placeholder {
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}
.spot-icon-large {
  font-size: 72px;
  filter: drop-shadow(0 0 20px rgba(74,222,128,0.3));
  animation: icon-float 3s ease-in-out infinite;
}
@keyframes icon-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.spot-icon-label {
  font-size: 16px; color: rgba(255,255,255,0.6);
  letter-spacing: 2px;
}
.spot-desc { font-size: 15px; line-height: 1.8; color: rgba(255,255,255,0.8); margin-bottom: 16px; }
.spot-location {
  display: flex; align-items: flex-start; gap: 6px;
  font-size: 13px; color: rgba(251,191,36,0.7);
  margin-bottom: 12px; line-height: 1.5;
}
.spot-location .location-icon { flex-shrink: 0; }
.spot-category-tag {
  display: inline-block; padding: 2px 10px;
  background: rgba(34,197,94,0.15); border: 1px solid rgba(34,197,94,0.3);
  border-radius: 10px; font-size: 11px; color: rgba(74,222,128,0.8);
  margin-bottom: 16px;
}
.spot-meta { display: flex; flex-direction: column; gap: 10px; margin-bottom: 24px; }
.meta-item { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.08); }
.meta-label { color: rgba(255,255,255,0.5); font-size: 14px; }
.guide-btn {
  width: 100%; padding: 16px; border-radius: 12px;
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
  border: none; color: #fff; font-size: 16px; font-weight: 600;
  cursor: pointer; transition: all 0.2s;
}
.guide-btn:hover { transform: scale(1.02); }

/* 屏保 */
.screensaver {
  position: fixed; inset: 0;
  background: linear-gradient(135deg, #0a1628, #1a2a4a);
  display: flex; align-items: center; justify-content: center;
  z-index: 999; cursor: pointer;
}
.screensaver-content { text-align: center; }
.ss-logo { font-size: 80px; margin-bottom: 20px; animation: float 3s ease-in-out infinite; }
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-16px); }
}
.screensaver-content h2 { font-size: 48px; font-weight: 700; margin-bottom: 12px; }
.screensaver-content p { font-size: 20px; color: rgba(255,255,255,0.6); margin-bottom: 40px; }
.ss-wave {
  display: flex; align-items: flex-end; justify-content: center; gap: 6px; height: 48px;
}
.ss-wave span {
  width: 6px; background: rgba(64,120,255,0.6); border-radius: 3px;
  animation: ssWave 1.2s ease-in-out infinite alternate;
}
.ss-wave span:nth-child(1) { height: 12px; }
.ss-wave span:nth-child(2) { height: 24px; animation-delay: 0.15s; }
.ss-wave span:nth-child(3) { height: 40px; animation-delay: 0.3s; }
.ss-wave span:nth-child(4) { height: 48px; animation-delay: 0.2s; }
.ss-wave span:nth-child(5) { height: 36px; animation-delay: 0.35s; }
.ss-wave span:nth-child(6) { height: 20px; animation-delay: 0.1s; }
.ss-wave span:nth-child(7) { height: 10px; animation-delay: 0.4s; }
.ss-wave span:nth-child(8) { height: 8px; animation-delay: 0.05s; }
@keyframes ssWave { to { height: 6px; } }

/* 过渡 */
.slide-enter-active, .slide-leave-active { transition: transform 0.3s ease; }
.slide-enter-from, .slide-leave-to { transform: translateX(100%); }
.fade-enter-active, .fade-leave-active { transition: opacity 0.5s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
.pop-enter-active, .pop-leave-active { transition: all 0.25s ease; }
.pop-enter-from, .pop-leave-to { opacity: 0; transform: scale(0.92) translateY(-12px); }

/* 人物切换动画 */
.avatar-switch-enter-active { transition: all 0.4s ease; }
.avatar-switch-leave-active { transition: all 0.3s ease; position: absolute; }
.avatar-switch-enter-from { opacity: 0; transform: translateY(20px) scale(0.9); }
.avatar-switch-leave-to { opacity: 0; transform: translateY(-20px) scale(0.9); }

/* ========== 人物切换按钮组 ========== */
.avatar-switch-bar {
  position: absolute;
  top: 36px; left: 36px;
  display: flex; gap: 8px;
  z-index: 50;
}
.avatar-switch-btn {
  display: flex; flex-direction: column; align-items: center; gap: 3px;
  padding: 8px 14px;
  background: rgba(0,0,0,0.45);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 14px; cursor: pointer; color: rgba(255,255,255,0.75);
  backdrop-filter: blur(10px);
  transition: all 0.22s ease;
  min-width: 58px;
}
.avatar-switch-btn:hover {
  background: rgba(255,255,255,0.15);
  border-color: rgba(255,255,255,0.45);
  color: #fff;
  transform: translateY(-2px);
}
.avatar-switch-btn.active {
  background: rgba(96,165,250,0.25);
  border-color: rgba(96,165,250,0.7);
  color: #93c5fd;
  box-shadow: 0 0 14px rgba(96,165,250,0.3);
}
.avatar-switch-btn.active[title="二次元"],
.avatar-switch-btn:nth-child(2).active {
  background: rgba(168,85,247,0.25);
  border-color: rgba(168,85,247,0.7);
  color: #c4b5fd;
  box-shadow: 0 0 14px rgba(168,85,247,0.3);
}
.avatar-switch-btn.active[title="仿生人"],
.avatar-switch-btn:nth-child(3).active {
  background: rgba(0,200,255,0.15);
  border-color: rgba(0,200,255,0.6);
  color: #67e8f9;
  box-shadow: 0 0 14px rgba(0,200,255,0.3);
}
.switch-icon { font-size: 20px; }
.switch-label { font-size: 11px; font-weight: 600; letter-spacing: 0.5px; }

/* ========== 虚拟键盘（大按钮触摸友好版） ========== */
.virtual-keyboard {
  background: linear-gradient(180deg, #374151 0%, #1f2937 100%);
  border-radius: 20px 20px 0 0;
  padding: 14px 16px;
  box-shadow: 0 -6px 24px rgba(0,0,0,0.4);
  position: relative;
  user-select: none;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.keyboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 4px 14px;
  border-bottom: 1px solid rgba(255,255,255,0.12);
  margin-bottom: 12px;
  color: #9ca3af;
  font-size: 14px;
  flex-shrink: 0;
}

.keyboard-mode-btns {
  display: flex;
  gap: 8px;
}

.mode-btn {
  background: rgba(255,255,255,0.1);
  border: none;
  color: #fff;
  padding: 8px 18px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
  min-width: 60px;
}

.mode-btn.active {
  background: #3b82f6;
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.4);
}

.mode-btn.symbol-btn.active {
  background: #8b5cf6;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.4);
}

.keyboard-close {
  background: rgba(255,255,255,0.08);
  border: none;
  color: #fff;
  padding: 8px 16px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.2s;
}

.keyboard-close:hover {
  background: rgba(255,255,255,0.15);
}

.keyboard-content {
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow: hidden;
}

.keyboard-row {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 6px;
}

/* 大尺寸触摸友好按键 */
.key {
  min-width: 38px;
  height: 58px;
  border: none;
  border-radius: 10px;
  background: #4b5563;
  color: #fff;
  font-size: 22px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.12s;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  flex: 1;
  max-width: 48px;
}

.key:active {
  background: #6b7280;
  transform: scale(0.94);
}

/* 数字键 */
.key.num-key {
  background: #374151;
  font-size: 24px;
}

/* 字母键 */
.key.letter-key {
  background: #4b5563;
}

/* 符号键 */
.key.symbol-key {
  background: #374151;
  font-size: 20px;
}

/* 功能键 */
.key.func-key {
  background: #5a6578;
  font-size: 16px;
  flex: 0;
  min-width: 55px;
  max-width: 65px;
}

/* Shift键激活状态 */
.key.shift-key.active {
  background: #3b82f6;
  box-shadow: inset 0 0 12px rgba(255,255,255,0.2);
}

/* 空格键 - 加宽 */
.key.space-key {
  flex: 2.5;
  min-width: 160px;
  max-width: 280px;
  font-size: 16px;
  background: #374151;
}

/* 回车键 - 绿色醒目 */
.key.enter-key {
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff;
  font-size: 16px;
  font-weight: 700;
  flex: 0;
  min-width: 80px;
  max-width: 100px;
}

.key.enter-key:active {
  background: linear-gradient(135deg, #059669, #047857);
}

/* 符号键盘行间距 */
.symbol-row {
  gap: 5px;
}

/* 数字行居中 */
.number-row {
  justify-content: center;
  gap: 5px;
}

/* 键盘弹出动画 */
.virtual-keyboard {
  animation: keyboardSlideUp 0.3s ease-out;
}

@keyframes keyboardSlideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 中英文切换按钮 */
.lang-toggle {
  background: linear-gradient(135deg, #6366f1, #4f46e5);
  border: none;
  color: #fff;
  padding: 8px 18px;
  border-radius: 10px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: all 0.2s;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}

.lang-toggle.active {
  background: linear-gradient(135deg, #10b981, #059669);
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.3);
}

.lang-toggle:hover {
  transform: scale(1.05);
}

/* 拼音输入区域 */
.pinyin-area {
  background: rgba(0,0,0,0.35);
  border-radius: 14px;
  padding: 14px 16px;
  margin-bottom: 12px;
  border: 1px solid rgba(255,255,255,0.08);
  flex-shrink: 0;
}

.pinyin-display {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}

.pinyin-text {
  font-size: 28px;
  color: #fff;
  font-weight: 600;
  letter-spacing: 3px;
  min-height: 38px;
  flex: 1;
}

.pinyin-hint {
  font-size: 13px;
  color: rgba(255,255,255,0.5);
  white-space: nowrap;
}

.clear-pinyin {
  background: rgba(239, 68, 68, 0.3);
  border: 1px solid rgba(239, 68, 68, 0.5);
  color: #fca5a5;
  padding: 6px 14px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}

.clear-pinyin:hover {
  background: rgba(239, 68, 68, 0.5);
}

.candidate-words-wrapper {
  overflow-x: auto;
  overflow-y: hidden;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;  /* Firefox */
  scroll-behavior: smooth;
}

.candidate-words-wrapper::-webkit-scrollbar {
  display: none;  /* Chrome/Safari */
}

.candidate-words {
  display: flex;
  gap: 8px;
  padding: 4px 0;
}

/* 候选词按钮 - 大尺寸触摸友好 */
.candidate-btn {
  min-width: 56px;
  height: 48px;
  padding: 0 14px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: 10px;
  color: #fff;
  font-size: 20px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 6px;
}

.candidate-num {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  background: rgba(255,255,255,0.1);
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.candidate-btn:hover, .candidate-btn.selected {
  background: linear-gradient(135deg, #10b981, #059669);
  border-color: #10b981;
  transform: scale(1.05);
}

.candidate-btn.selected {
  box-shadow: 0 2px 12px rgba(16, 185, 129, 0.4);
}

/* ========== SadTalker 数字人样式（三态：待机/生成中/讲解） ========== */
/* SadTalker 独立舞台：基于视口固定尺寸（再次放大10%），展开时不缩放 */
.sadtalker-stage {
  position: absolute;
  /* 基础尺寸再放大10%（累计2.06倍） */
  width: min(103vh, 92vw);
  height: min(145vh, 100vh);
  /* 始终在avatar-section内居中 */
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.sadtalker-stage > .sadtalker-wrapper,
.sadtalker-stage > .sadtalker-wrapper > div {
  pointer-events: auto;
}

.sadtalker-wrapper {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  min-height: 400px;
}

/* 待机状态 */
.sadtalker-idle {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  border-radius: 24px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  position: relative;
  transition: opacity 0.25s ease;
}

/* speaking 时待机层微微降低透明度，让上层视频出现时更平滑 */
.sadtalker-idle.idle-dimmed {
  opacity: 0.3;
}

/* 待机视频：占满容器，保持比例 */
.idle-video {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: #1a1a2e;
}

/* 待机静态图片 fallback */
.idle-fallback {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #1a1a2e;
}

.idle-fallback .idle-avatar {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.idle-hint {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 20px;
  background: rgba(0,0,0,0.5);
  border-radius: 20px;
  color: rgba(255,255,255,0.9);
  font-size: 14px;
  white-space: nowrap;
  z-index: 2;
  animation: fade-in-up 1s ease-out;
  backdrop-filter: blur(4px);
}

@keyframes idle-breathe {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-5px) scale(1.02); }
}

@keyframes fade-in-up {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

/* 生成中状态 */
.sadtalker-generating {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  border-radius: 24px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

/* 思考/生成中遮罩层：半透明覆盖在待机视频上方 */
.sadtalker-thinking-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.35);
  backdrop-filter: blur(2px);
  border-radius: 24px;
  z-index: 5;
}

.generating-avatar {
  position: relative;
  width: 200px;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.generating-img {
  width: 160px;
  height: 160px;
  object-fit: contain;
  border-radius: 12px;
  opacity: 0.7;
}

.generating-ring {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 180px;
  height: 180px;
  border: 3px solid rgba(99, 179, 237, 0.3);
  border-top-color: rgba(99, 179, 237, 0.9);
  border-radius: 50%;
  animation: spin 1.2s linear infinite;
}

@keyframes spin {
  to { transform: translate(-50%, -50%) rotate(360deg); }
}

.generating-text {
  margin-top: 20px;
  color: rgba(255,255,255,0.7);
  font-size: 15px;
}

.generating-dots {
  margin-top: 12px;
  display: flex;
  gap: 6px;
}

/* 讲解视频覆盖层 */
.sadtalker-video-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.4);
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  z-index: 3;
}

.sadtalker-video-overlay video {
  width: 100%;
  height: 100%;
  object-fit: contain;
  background: transparent;
}

/* ========== SadTalker 视频覆盖层 ========== */
.pinyin-guide {
  color: rgba(255,255,255,0.4);
  font-size: 14px;
}

/* ========== 聊天面板展开/收缩动画 - 从右侧边缘滑入 ========== */
.slide-from-right-enter-active {
  transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-from-right-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}
.slide-from-right-enter-from {
  opacity: 0;
  transform: translateX(100%);
}
.slide-from-right-leave-to {
  opacity: 0;
  transform: translateX(100%);
}

/* ===== Header Actions ===== */
.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-right: 12px;
  position: relative;
}
.header-action-btn {
  background: rgba(255,255,255,0.15);
  border: 1px solid rgba(255,255,255,0.25);
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(8px);
}
.header-action-btn:hover { background: rgba(255,255,255,0.25); transform: translateY(-1px); }
.header-action-btn.complaint-btn { background: rgba(245,108,108,0.25); border-color: rgba(245,108,108,0.4); }
.header-action-btn.complaint-btn:hover { background: rgba(245,108,108,0.4); }
.tourist-badge {
  background: rgba(64,158,255,0.3);
  border: 1px solid rgba(64,158,255,0.5);
  color: #fff;
  padding: 6px 14px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.tourist-badge:hover { background: rgba(64,158,255,0.5); }

/* ===== 游客快捷弹窗 ===== */
.tourist-popup {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 8px;
  background: rgba(20, 30, 55, 0.96);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(64,158,255,0.4);
  border-radius: 10px;
  min-width: 140px;
  z-index: 200;
  box-shadow: 0 8px 32px rgba(0,0,0,0.4);
  overflow: hidden;
}
.tourist-popup-item {
  padding: 10px 16px;
  font-size: 13px;
  color: #e2e8f0;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 6px;
}
.tourist-popup-item:hover {
  background: rgba(245,108,108,0.25);
  color: #fca5a5;
}

/* ===== Modal Overlay ===== */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.5);
  backdrop-filter: blur(4px);
  display: flex; align-items: center; justify-content: center;
  z-index: 9999;
}
.modal-card {
  background: #fff;
  border-radius: 16px;
  padding: 28px;
  width: 420px;
  max-width: 90vw;
  position: relative;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3);
  animation: modalIn 0.3s ease;
}
@keyframes modalIn { from { opacity: 0; transform: scale(0.9) translateY(20px); } to { opacity: 1; transform: scale(1) translateY(0); } }
.modal-card h3 { margin: 0 0 20px; font-size: 20px; color: #1a1a1a; }
.modal-close {
  position: absolute; top: 16px; right: 16px;
  background: none; border: none; font-size: 18px; cursor: pointer; color: #999;
  width: 32px; height: 32px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
}
.modal-close:hover { background: #f5f5f5; color: #333; }
.modal-input {
  width: 100%; padding: 10px 14px; border: 1px solid #e0e0e0; border-radius: 8px;
  font-size: 14px; box-sizing: border-box; margin-bottom: 12px; outline: none; transition: border-color 0.2s;
}
.modal-input:focus { border-color: #409eff; }
.modal-textarea {
  width: 100%; padding: 10px 14px; border: 1px solid #e0e0e0; border-radius: 8px;
  font-size: 14px; box-sizing: border-box; margin-bottom: 12px; outline: none; resize: vertical; transition: border-color 0.2s;
  font-family: inherit;
}
.modal-textarea:focus { border-color: #409eff; }
.modal-submit-btn {
  width: 100%; padding: 12px; background: #409eff; color: #fff; border: none;
  border-radius: 8px; font-size: 15px; cursor: pointer; transition: all 0.2s; font-weight: 600;
}
.modal-submit-btn:hover { background: #337ecc; }
.modal-submit-btn:disabled { background: #a0cfff; cursor: not-allowed; }
.modal-switch { text-align: center; margin-top: 14px; font-size: 13px; color: #999; }
.modal-switch a { color: #409eff; text-decoration: none; }

/* ===== Complaint Specific ===== */
.complaint-type-tabs { display: flex; gap: 0; margin-bottom: 16px; border-radius: 8px; overflow: hidden; border: 1px solid #e0e0e0; }
.complaint-type-tabs button {
  flex: 1; padding: 10px; border: none; background: #f9f9f9; font-size: 14px; cursor: pointer; transition: all 0.2s;
}
.complaint-type-tabs button.active { background: #409eff; color: #fff; }
.complaint-select {
  width: 100%; padding: 10px 14px; border: 1px solid #e0e0e0; border-radius: 8px;
  font-size: 14px; box-sizing: border-box; margin-bottom: 12px; outline: none; background: #fff;
  appearance: auto;
}

/* ===== Spot Reviews ===== */
.spot-reviews-section {
  margin-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.15);
  padding-top: 14px;
}
.reviews-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.reviews-title { font-size: 15px; font-weight: 600; color: #fff; }
.reviews-avg { font-size: 13px; color: #e6a23c; font-weight: 600; }
.review-form { margin-bottom: 12px; }
.review-stars { display: flex; gap: 4px; }
.star-btn { font-size: 24px; color: rgba(255,255,255,0.3); cursor: pointer; transition: color 0.15s; background: none; border: none; padding: 0; }
.star-btn.active { color: #e6a23c; }
.star-btn:hover { color: #f0c78a; }
.review-input {
  flex: 1; padding: 8px 12px; border: 1px solid rgba(255,255,255,0.2); border-radius: 6px;
  font-size: 13px; outline: none; background: rgba(255,255,255,0.1); color: #fff;
}
.review-input::placeholder { color: rgba(255,255,255,0.4); }
.review-input:focus { border-color: #409eff; }
.review-submit-btn {
  padding: 8px 16px; background: #409eff; color: #fff; border: none;
  border-radius: 6px; font-size: 13px; cursor: pointer; white-space: nowrap;
}
.review-submit-btn:disabled { background: #a0cfff; cursor: not-allowed; }
.review-login-hint { font-size: 13px; color: rgba(255,255,255,0.5); margin-bottom: 12px; padding: 8px 0; }
.review-login-hint a { color: #409eff; text-decoration: none; }
.reviews-list { max-height: 240px; overflow-y: auto; }
.review-item { padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.1); }
.review-item:last-child { border-bottom: none; }
.review-item-header { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.reviewer-name { font-size: 13px; font-weight: 600; color: #fff; }
.review-stars-sm { font-size: 12px; color: #e6a23c; letter-spacing: -1px; }
.review-time { font-size: 11px; color: rgba(255,255,255,0.45); margin-left: auto; }
.review-content { font-size: 13px; color: rgba(255,255,255,0.85); line-height: 1.5; }
.reviews-empty { text-align: center; color: rgba(255,255,255,0.5); font-size: 13px; padding: 20px 0; }

/* Make spot-detail-panel scrollable for reviews */
.spot-detail-panel { max-height: calc(100vh - 100px); overflow-y: auto; }

/* ═══════════════════════════════════════════════════════════
   手机端适配 (≤768px)
   电脑端布局不变，手机端采用垂直堆叠 + 抽屉式面板
   ═══════════════════════════════════════════════════════════ */
@media (max-width: 768px) {
  /* ===== 顶部栏：紧凑 ===== */
  .kiosk-header {
    height: 52px;
    padding: 0 10px;
    gap: 6px;
  }
  .header-left { gap: 8px; }
  .logo { width: 30px; height: 30px; border-radius: 6px; }
  .scenic-name { font-size: 15px; }
  .current-spot { font-size: 10px; display: none; }
  /* 隐藏中间状态栏 */
  .header-center { display: none; }
  .header-right { gap: 8px; }
  /* 登录/投诉按钮在手机端用更小的图标 */
  .header-actions { gap: 4px; }
  .header-action-btn {
    font-size: 11px; padding: 4px 8px; border-radius: 6px;
  }
  .tourist-badge { font-size: 12px; padding: 4px 10px; }
  .time { font-size: 15px; }
  .date { font-size: 10px; display: none; }
  .weather { font-size: 13px; gap: 3px; }

  /* ===== 主内容：垂直堆叠 ===== */
  .kiosk-main {
    flex-direction: column;
    height: calc(100vh - 52px);
  }

  /* ===== 中间数字人区：固定顶部 38% 高度 ===== */
  .avatar-section {
    flex: 0 0 38vh;
    width: 100%;
    padding: 6px;
    border-right: none !important;
    border-left: none !important;
    border-bottom: 1px solid rgba(255,255,255,0.1);
    overflow: hidden;
  }
  .avatar-section.chat-open,
  .avatar-section.spot-open,
  .avatar-section.chat-open.spot-open {
    flex: 0 0 32vh;
    border-right: none !important;
    border-left: none !important;
  }
  /* 手机端隐藏景区背景水印，避免干扰 */
  .spot-bg::after { font-size: 80px; }

  /* ===== 左侧景点面板：浮层抽屉 ===== */
  .spot-section {
    position: fixed;
    top: 0; left: 0; bottom: 0;
    width: 0;
    z-index: 500;
    transition: width 0.3s ease;
  }
  .spot-section.expanded {
    width: 85vw !important;
  }
  .spot-list-panel {
    border-radius: 0;
    border-right: 2px solid rgba(34,197,94,0.5);
  }
  .spot-list-header { padding: 12px 14px; }
  .spot-list-header h3 { font-size: 15px; }
  .view-toggle button { padding: 4px 8px; font-size: 10px; }

  /* ===== 右侧交互区：填充剩余高度 ===== */
  .interaction-section {
    flex: 1;
    width: 100% !important;
    padding: 6px !important;
    min-height: 0;
    gap: 6px;
  }
  .interaction-section.expanded {
    width: 100% !important;
    padding: 6px !important;
  }

  /* 聊天面板 */
  .chat-panel {
    border-radius: 10px;
    flex: 1;
    min-height: 0;
  }
  .chat-header { padding: 10px 14px; }
  .chat-header h3 { font-size: 14px; }
  .chat-messages { padding: 10px; gap: 10px; }
  .message-bubble { font-size: 13px; max-width: 85%; }
  .message-bubble p { font-size: 13px; line-height: 1.5; }
  .message-time { font-size: 10px; }
  .chat-empty p { font-size: 13px; }

  /* 输入面板 */
  .input-panel { padding: 8px; border-radius: 10px; gap: 6px; }
  .input-row { gap: 5px; }
  .text-input {
    padding: 10px 12px; font-size: 14px; border-radius: 10px;
  }
  .voice-btn {
    width: 42px; height: 42px; border-radius: 10px; font-size: 18px;
  }
  .send-btn {
    height: 42px; padding: 0 14px; border-radius: 10px; font-size: 13px;
  }
  .abort-btn {
    height: 42px; padding: 0 14px; border-radius: 10px; font-size: 13px;
  }
  .quick-questions { gap: 5px; }
  .quick-btn {
    padding: 4px 10px; font-size: 11px; border-radius: 16px;
  }

  /* 思考中提示 */
  .thinking-tip { font-size: 12px; padding: 6px; }
  .voice-status { font-size: 12px; padding: 6px; }

  /* ===== 左右切换按钮：缩小并适配位置 ===== */
  .spot-toggle-btn {
    width: 28px; height: 52px;
    border-radius: 0 14px 14px 0;
    z-index: 501;
  }
  .spot-toggle-btn.expanded {
    left: calc(85vw - 34px);
    border-radius: 14px 0 0 14px;
  }
  .chat-toggle-btn {
    width: 28px; height: 52px;
    border-radius: 14px 0 0 14px;
    z-index: 100;
  }
  .toggle-text { font-size: 11px; letter-spacing: 1px; }

  /* ===== SadTalker 数字人区域缩放 ===== */
  .sadtalker-stage { padding: 0; }
  .sadtalker-idle { border-radius: 8px; }
  .idle-video { object-fit: contain; }
  .idle-fallback .idle-avatar { width: 100%; height: 100%; }
  .idle-hint { font-size: 12px; bottom: 8px; }

  /* 思考/生成遮罩 */
  .sadtalker-thinking-overlay { border-radius: 8px; }
  .thinking-avatar { width: 80px; height: 80px; }
  .generating-ring { width: 90px; height: 90px; border-width: 2px; }
  .generating-text { font-size: 12px; margin-top: 10px; }
  .thinking-dots span { width: 6px; height: 6px; }

  /* 讲解视频覆盖层 */
  .sadtalker-video-overlay { border-radius: 8px; }
  .sadtalker-video { object-fit: contain; }

  /* ===== 景点详情面板：全屏浮层 ===== */
  .spot-detail-panel {
    width: 100% !important;
    max-width: 100vw;
    top: 0;
    bottom: 0;
    z-index: 600;
    border-radius: 0;
    padding: 16px;
    max-height: 100vh;
    border-left: none;
  }
  .spot-detail-panel h2 { font-size: 18px; margin-bottom: 10px; padding-right: 36px; }
  .spot-detail-image { max-height: 160px; }
  .spot-desc { font-size: 13px; }
  .spot-meta { gap: 8px; }
  .meta-item { font-size: 12px; }
  .guide-btn { padding: 10px; font-size: 14px; }
  .close-panel { top: 10px; right: 10px; width: 28px; height: 28px; font-size: 14px; }

  /* ===== 弹窗：全屏适配 ===== */
  .modal-overlay { padding: 12px; }
  .modal-card {
    width: 92vw;
    max-height: 85vh;
    overflow-y: auto;
    padding: 20px 16px;
    border-radius: 14px;
  }
  .modal-card h3 { font-size: 17px; }
  .modal-input, .modal-textarea, .complaint-select {
    font-size: 14px; padding: 10px 12px;
  }
  .modal-submit-btn { padding: 12px; font-size: 15px; }
  .modal-close { top: 8px; right: 10px; font-size: 16px; }

  /* ===== 虚拟键盘：跨全宽 ===== */
  .virtual-keyboard {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 700;
    border-radius: 16px 16px 0 0;
  }
  .keyboard-header { padding: 8px 12px; }
  .keyboard-header span { font-size: 12px; }
  .keyboard-mode-btns { gap: 3px; }
  .mode-btn { padding: 2px 6px; font-size: 10px; }
  .keyboard-close { font-size: 12px; padding: 4px 8px; }
  .keyboard-content .key {
    min-width: 0;
    padding: 8px 2px;
    font-size: 13px;
    border-radius: 6px;
  }
  .keyboard-row { gap: 3px; margin-bottom: 3px; }
  .keyboard-content { padding: 8px 4px; }
  .pinyin-area { padding: 6px 8px; }
  .pinyin-text { font-size: 16px; }
  .candidate-btn { font-size: 12px; padding: 4px 8px; }

  /* ===== 天气弹窗：全屏 ===== */
  /* WeatherPopup 组件内部自行适配，此处仅作容器调整 */

  /* ===== 换装面板：全屏浮层 ===== */
  .outfit-panel {
    position: fixed;
    top: 5vh;
    left: 2vw;
    right: 2vw;
    bottom: 5vh;
    width: auto;
    max-height: none;
    border-radius: 14px;
    z-index: 550;
  }

  /* ===== 屏保缩放 ===== */
  .screensaver-content h2 { font-size: 22px; }
  .screensaver-content p { font-size: 13px; }
  .ss-logo { font-size: 48px; }
  .ss-wave span { width: 24px; height: 2px; }

  /* ===== 手机端隐藏一些 hover 效果 ===== */
  .spot-list-item:hover { transform: none; }

  /* ===== 评论区域 ===== */
  .reviews-list { max-height: 150px; }
  .star-btn { font-size: 20px; }
  .review-input { font-size: 12px; }
  .review-submit-btn { font-size: 12px; padding: 6px 12px; }

  /* ===== 游客快捷弹窗 ===== */
  .tourist-popup {
    position: fixed;
    top: 52px;
    right: 8px;
    z-index: 450;
  }
}

/* ===== 音频提示（状态栏内联显示） ===== */
.audio-hint {
  margin-left: 12px;
  padding: 3px 10px;
  background: rgba(255, 193, 7, 0.2);
  border: 1px solid rgba(255, 193, 7, 0.5);
  border-radius: 12px;
  font-size: 12px;
  color: #ffc107;
  cursor: pointer;
  white-space: nowrap;
  animation: audio-hint-blink 0.8s ease 3;
}
@keyframes audio-hint-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
</style>

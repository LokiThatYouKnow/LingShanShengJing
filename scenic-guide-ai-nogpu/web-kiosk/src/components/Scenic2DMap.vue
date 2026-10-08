<template>
  <div class="scenic-2d-map" ref="mapRoot">
    <!-- 隐藏的 SVG 渲染源（用于序列化为 Leaflet 底图） -->
    <div class="svg-source" ref="svgSource">
      <svg
        class="guide-map-svg"
        viewBox="-30 -30 480 840"
        width="960"
        height="1680"
      >
        <defs>
          <!-- 背景渐变 -->
          <linearGradient id="paperBg" x1="0" y1="0" x2="0.15" y2="1">
            <stop offset="0%"   stop-color="#fbf6e8"/>
            <stop offset="15%"  stop-color="#f7efd8"/>
            <stop offset="40%"  stop-color="#f2e6c8"/>
            <stop offset="75%"  stop-color="#efe0bc"/>
            <stop offset="100%" stop-color="#ebd8aa"/>
          </linearGradient>
          <!-- 远山 -->
          <linearGradient id="mtFar" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stop-color="#b8cec0" stop-opacity="0.50"/>
            <stop offset="40%"  stop-color="#c5d6cc" stop-opacity="0.30"/>
            <stop offset="100%" stop-color="#dce4df" stop-opacity="0.05"/>
          </linearGradient>
          <!-- 近山 -->
          <linearGradient id="mtNear" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stop-color="#8daa8a"/>
            <stop offset="30%"  stop-color="#a3bba0"/>
            <stop offset="65%"  stop-color="#bccfb5"/>
            <stop offset="100%" stop-color="#d5e0cc"/>
          </linearGradient>
          <!-- 太湖 -->
          <linearGradient id="lakeGrad" x1="0" y1="0" x2="1" y2="0.3">
            <stop offset="0%"   stop-color="rgba(110,175,220,0.50)"/>
            <stop offset="30%"  stop-color="rgba(90,160,210,0.38)"/>
            <stop offset="60%"  stop-color="rgba(75,148,200,0.25)"/>
            <stop offset="100%" stop-color="rgba(60,130,185,0.10)"/>
          </linearGradient>
          <!-- 香水海 -->
          <radialGradient id="seaGrad" cx="48%" cy="45%" r="55%">
            <stop offset="0%"   stop-color="rgba(85,170,225,0.55)"/>
            <stop offset="35%"  stop-color="rgba(65,152,210,0.35)"/>
            <stop offset="70%"  stop-color="rgba(50,135,195,0.15)"/>
            <stop offset="100%" stop-color="rgba(40,120,180,0.04)"/>
          </radialGradient>
          <!-- 路线渐变 -->
          <linearGradient id="routeGrad" x1="0" y1="1" x2="0" y2="0">
            <stop offset="0%"   stop-color="#c48820"/>
            <stop offset="45%"  stop-color="#daa520"/>
            <stop offset="100%" stop-color="#f0c848"/>
          </linearGradient>
          <!-- 阴影 -->
          <filter id="shadow">
            <feDropShadow dx="1.5" dy="2.5" stdDeviation="2" flood-opacity="0.22"/>
          </filter>
          <filter id="shadowSm">
            <feDropShadow dx="0.8" dy="1.2" stdDeviation="1" flood-opacity="0.18"/>
          </filter>
          <!-- 发光 -->
          <filter id="glow">
            <feGaussianBlur stdDeviation="2.2" result="blur"/>
            <feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge>
          </filter>
          <!-- 树模板 -->
          <g id="tree1">
            <circle cx="0" cy="-5" r="7.5" fill="rgba(80,138,65,0.36)" stroke="rgba(65,115,50,0.20)" stroke-width="0.5"/>
            <circle cx="0" cy="-7" r="5" fill="rgba(100,158,80,0.28)"/>
            <line x1="0" y1="0" x2="0" y2="5" stroke="rgba(120,90,55,0.30)" stroke-width="1.5"/>
          </g>
          <g id="tree2">
            <circle cx="0" cy="-3.5" r="5.5" fill="rgba(72,125,55,0.32)" stroke="rgba(55,100,40,0.16)" stroke-width="0.4"/>
            <circle cx="0" cy="-5" r="3.8" fill="rgba(88,142,70,0.24)"/>
            <line x1="0" y1="0" x2="0" y2="3.5" stroke="rgba(120,90,55,0.25)" stroke-width="1.2"/>
          </g>
          <g id="tree3">
            <ellipse cx="0" cy="-8" rx="8" ry="10" fill="rgba(90,150,72,0.30)" stroke="rgba(70,125,55,0.15)" stroke-width="0.5"/>
            <ellipse cx="-4" cy="-3" rx="6" ry="7" fill="rgba(100,160,80,0.22)"/>
            <ellipse cx="4" cy="-2" rx="5.5" ry="6.5" fill="rgba(95,155,78,0.24)"/>
            <rect x="-1.5" y="0" width="3" height="6" rx="1" fill="rgba(130,100,60,0.28)"/>
          </g>
          <!-- 云 -->
          <g id="cloud">
            <ellipse cx="0" cy="0" rx="16" ry="6" fill="rgba(255,255,255,0.55)"/>
            <ellipse cx="-10" cy="1.5" rx="10" ry="5" fill="rgba(255,255,255,0.48)"/>
            <ellipse cx="10" cy="1.5" rx="9" ry="4.5" fill="rgba(255,255,255,0.42)"/>
          </g>
          <!-- 装饰边框图案 -->
          <pattern id="borderPattern" x="0" y="0" width="20" height="20" patternUnits="userSpaceOnUse">
            <circle cx="10" cy="10" r="0.8" fill="rgba(180,150,100,0.25)"/>
            <circle cx="0" cy="0" r="0.5" fill="rgba(180,150,100,0.12)"/>
          </pattern>
        </defs>

        <!-- L0: 底纸 -->
        <rect x="-30" y="-30" width="480" height="840" fill="url(#paperBg)" rx="10"/>
        <!-- 内边框 -->
        <rect x="-26" y="-26" width="472" height="832" rx="8"
              fill="none" stroke="rgba(180,140,90,0.30)" stroke-width="1.5"/>
        <rect x="-23" y="-23" width="466" height="826" rx="7"
              fill="none" stroke="rgba(180,140,90,0.12)" stroke-width="0.8"/>
        <rect x="-27" y="-27" width="474" height="834" rx="9"
              fill="url(#borderPattern)" opacity="0.7"/>

        <g transform="translate(30, 30)">
        <!-- L1: 远山层（北部群山） -->
        <path d="M-5,180 Q30,100 70,52 Q105,16 150,10 Q195,4 238,12 Q280,20 310,45 Q355,78 400,140 Q430,190 440,250
                 Q425,200 395,155 Q360,110 318,78 Q275,48 235,35 Q195,22 150,28 Q108,38 70,72 Q35,118 0,180 Z"
              fill="url(#mtFar)"/>
        <path d="M10,195 Q50,120 100,65 Q145,28 195,18 Q240,10 278,22 Q320,40 362,80 Q395,122 420,178 Q435,230 440,270
                 Q420,210 390,165 Q355,118 315,85 Q278,58 240,42 Q198,28 155,38 Q110,52 70,88 Q35,135 5,200 Z"
              fill="url(#mtNear)" opacity="0.52"/>
        <!-- 西侧山丘 -->
        <path d="M-5,320 Q30,240 65,210 Q90,195 115,205 Q105,215 95,236 Q78,268 55,310 Q35,345 -5,380 Z"
              fill="rgba(140,160,130,0.22)"/>
        <path d="M-5,500 Q25,440 50,420 Q70,408 90,418 Q78,430 65,452 Q48,485 30,520 Q15,550 -5,565 Z"
              fill="rgba(145,165,135,0.18)"/>

        <!-- 祥云 -->
        <use href="#cloud" x="55" y="55" transform="scale(0.85)"/>
        <use href="#cloud" x="260" y="30" transform="scale(0.70)"/>
        <use href="#cloud" x="360" y="65" transform="scale(0.55)"/>
        <use href="#cloud" x="180" y="28" transform="scale(0.60)"/>
        <use href="#cloud" x="320" y="45" transform="scale(0.50)"/>

        <!-- L2: 水系 -->
        <!-- 太湖（底部） -->
        <path d="M-5,712 Q55,698 140,702 Q230,695 320,700 Q400,706 430,712 L430,790 L-5,790 Z"
              fill="url(#lakeGrad)"/>
        <path d="M0,720 Q40,716 80,720 Q120,724 160,720 Q200,716 240,720 Q280,724 320,720 Q360,716 400,720 Q420,724 430,720"
              fill="none" stroke="rgba(120,185,225,0.30)" stroke-width="1.6"/>
        <path d="M0,728 Q50,724 100,728 Q150,732 200,728 Q250,724 300,728 Q350,732 400,728"
              fill="none" stroke="rgba(120,185,225,0.20)" stroke-width="1.2"/>
        <path d="M10,736 Q80,732 150,736 Q220,732 290,736 Q360,732 420,736"
              fill="none" stroke="rgba(120,185,225,0.12)" stroke-width="0.9"/>
        <path d="M20,744 Q100,740 180,744 Q260,740 340,744 Q400,742 425,744"
              fill="none" stroke="rgba(120,185,225,0.07)" stroke-width="0.7"/>
        <!-- 太湖帆船 -->
        <g transform="translate(180, 758)" opacity="0.30">
          <line x1="0" y1="0" x2="0" y2="10" stroke="#8b7355" stroke-width="0.8"/>
          <path d="M0,0 L12,6 L0,8 Z" fill="rgba(220,210,180,0.7)"/>
        </g>
        <g transform="translate(320, 762)" opacity="0.25">
          <line x1="0" y1="0" x2="0" y2="8" stroke="#8b7355" stroke-width="0.7"/>
          <path d="M0,0 L10,5 L0,7 Z" fill="rgba(220,210,180,0.6)"/>
        </g>
        <text x="210" y="775" text-anchor="middle" font-size="11"
              fill="rgba(75,135,180,0.55)" font-style="italic" letter-spacing="5"
              font-family="'KaiTi','STKaiti','SimSun',serif">— 太 湖 万 顷 —</text>

        <!-- 香水海（中轴线右侧，占据主轴线与东翼之间的空间） -->
        <path d="M265,260 Q290,240 320,248 Q355,258 350,295 Q356,330 345,365
                 Q332,400 310,412 Q288,420 270,408 Q252,396 258,360
                 Q250,335 256,300 Q260,275 265,260 Z"
              fill="url(#seaGrad)" stroke="rgba(100,168,218,0.36)" stroke-width="1.8"/>
        <path d="M260,278 Q298,268 340,278" fill="none" stroke="rgba(135,195,235,0.26)" stroke-width="1.2"/>
        <path d="M258,310 Q295,302 342,312" fill="none" stroke="rgba(135,195,235,0.22)" stroke-width="1.1"/>
        <path d="M256,345 Q290,336 338,346" fill="none" stroke="rgba(135,195,235,0.26)" stroke-width="1.2"/>
        <path d="M260,375 Q290,368 330,378" fill="none" stroke="rgba(135,195,235,0.18)" stroke-width="1.0"/>
        <text x="298" y="328" text-anchor="middle" font-size="9"
              fill="rgba(75,135,180,0.54)" letter-spacing="3">香 水 海</text>
        <!-- 湖心岛（五印坛城所在） -->
        <ellipse cx="305" cy="310" rx="22" ry="15" fill="rgba(215,200,170,0.62)"
                 stroke="rgba(155,135,105,0.34)" stroke-width="1.3"/>

        <!-- 东侧小湖/池塘 -->
        <ellipse cx="370" cy="450" rx="18" ry="10" fill="rgba(85,170,220,0.22)"
                 stroke="rgba(95,165,218,0.22)" stroke-width="0.9"/>
        <ellipse cx="385" cy="445" rx="12" ry="7" fill="rgba(90,172,222,0.16)"/>

        <!-- 玉带河（底部，横跨入口区） -->
        <path d="M60,670 Q140,655 220,660 Q300,656 360,668"
              fill="none" stroke="rgba(105,168,215,0.48)" stroke-width="6"/>
        <path d="M65,676 Q145,661 225,666 Q305,662 355,674"
              fill="none" stroke="rgba(105,168,215,0.24)" stroke-width="3.5"/>
        <text x="210" y="665" text-anchor="middle" font-size="7"
              fill="rgba(65,130,175,0.48)" letter-spacing="2">玉 带 河</text>

        <!-- 东侧小溪 -->
        <path d="M350,380 Q360,420 370,450" fill="none" stroke="rgba(105,168,215,0.28)" stroke-width="3"/>
        <path d="M355,385 Q363,420 372,448" fill="none" stroke="rgba(105,168,215,0.14)" stroke-width="1.5"/>

        <!-- L3: 植被层（大量树木填充空白区域） -->
        <!-- 西侧竹林/阔叶林（无尽意斋周边） -->
        <circle cx="75" cy="565" r="22" fill="rgba(85,155,72,0.13)"/>
        <circle cx="100" cy="545" r="20" fill="rgba(85,155,72,0.11)"/>
        <circle cx="65" cy="600" r="18" fill="rgba(85,155,72,0.10)"/>
        <use href="#tree3" x="72" y="570"/><use href="#tree3" x="95" y="548"/>
        <use href="#tree2" x="62" y="590"/><use href="#tree2" x="82" y="555"/>
        <use href="#tree2" x="105" y="535"/><use href="#tree2" x="68" y="610"/>
        <use href="#tree1" x="58" y="578"/><use href="#tree1" x="90" y="530"/>
        <use href="#tree1" x="110" y="555"/><use href="#tree3" x="80" y="600"/>
        <use href="#tree2" x="55" y="555"/><use href="#tree2" x="95" y="575"/>
        <use href="#tree2" x="115" y="568"/><use href="#tree1" x="75" y="585"/>
        <!-- 更远的西侧山林 -->
        <circle cx="50" cy="520" r="18" fill="rgba(80,145,68,0.08)"/>
        <circle cx="40" cy="480" r="16" fill="rgba(80,145,68,0.07)"/>
        <use href="#tree3" x="48" y="522"/><use href="#tree2" x="42" y="482"/>
        <use href="#tree1" x="55" y="505"/><use href="#tree2" x="38" y="495"/>

        <!-- 西侧山间林木 -->
        <circle cx="30" cy="400" r="15" fill="rgba(85,150,72,0.07)"/>
        <circle cx="45" cy="350" r="14" fill="rgba(85,150,72,0.06)"/>
        <use href="#tree2" x="28" y="402"/><use href="#tree2" x="43" y="352"/>
        <use href="#tree3" x="35" y="375"/><use href="#tree1" x="48" y="365"/>

        <!-- 北山森林（大佛周边山体植被） -->
        <circle cx="210" cy="85" r="25" fill="rgba(75,140,65,0.12)"/>
        <circle cx="250" cy="75" r="22" fill="rgba(75,140,65,0.10)"/>
        <circle cx="180" cy="100" r="20" fill="rgba(75,140,65,0.09)"/>
        <circle cx="270" cy="95" r="18" fill="rgba(80,145,68,0.08)"/>
        <use href="#tree3" x="208" y="88"/><use href="#tree3" x="252" y="78"/>
        <use href="#tree2" x="182" y="102"/><use href="#tree2" x="268" y="97"/>
        <use href="#tree2" x="225" y="82"/><use href="#tree1" x="195" y="95"/>
        <use href="#tree1" x="240" y="72"/><use href="#tree1" x="260" y="85"/>
        <use href="#tree3" x="175" y="110"/><use href="#tree2" x="258" y="68"/>
        <use href="#tree1" x="218" y="75"/><use href="#tree2" x="280" y="88"/>

        <!-- 主路两侧行道树（沿中轴线 dense planting） -->
        <use href="#tree1" x="282" y="700"/><use href="#tree2" x="290" y="710"/>
        <use href="#tree2" x="275" y="695"/><use href="#tree1" x="278" y="705"/>
        <use href="#tree1" x="280" y="668"/><use href="#tree2" x="284" y="676"/>
        <use href="#tree2" x="273" y="663"/><use href="#tree1" x="277" y="672"/>
        <use href="#tree1" x="276" y="630"/><use href="#tree2" x="280" y="638"/>
        <use href="#tree2" x="270" y="626"/><use href="#tree1" x="274" y="634"/>
        <use href="#tree1" x="272" y="578"/><use href="#tree2" x="276" y="586"/>
        <use href="#tree2" x="266" y="574"/><use href="#tree1" x="270" y="582"/>
        <use href="#tree1" x="268" y="488"/><use href="#tree2" x="272" y="498"/>
        <use href="#tree2" x="262" y="484"/><use href="#tree1" x="266" y="494"/>
        <use href="#tree1" x="261" y="420"/><use href="#tree2" x="265" y="430"/>
        <use href="#tree2" x="255" y="416"/><use href="#tree1" x="259" y="426"/>
        <use href="#tree1" x="255" y="362"/><use href="#tree2" x="259" y="372"/>
        <use href="#tree2" x="249" y="358"/><use href="#tree1" x="253" y="368"/>
        <use href="#tree1" x="250" y="318"/><use href="#tree2" x="254" y="328"/>
        <use href="#tree2" x="244" y="314"/><use href="#tree1" x="248" y="324"/>

        <!-- 香水海周边树群（水岸植被） -->
        <circle cx="278" cy="285" r="16" fill="rgba(80,140,68,0.10)"/>
        <circle cx="355" cy="310" r="15" fill="rgba(80,140,68,0.09)"/>
        <circle cx="345" cy="250" r="14" fill="rgba(80,140,68,0.08)"/>
        <use href="#tree3" x="276" y="288"/><use href="#tree1" x="268" y="295"/>
        <use href="#tree2" x="285" y="280"/><use href="#tree3" x="353" y="313"/>
        <use href="#tree2" x="342" y="305"/><use href="#tree1" x="358" y="308"/>
        <use href="#tree1" x="343" y="252"/><use href="#tree2" x="338" y="248"/>
        <use href="#tree2" x="295" y="400"/><use href="#tree1" x="300" y="395"/>
        <use href="#tree1" x="270" y="355"/><use href="#tree2" x="275" y="362"/>
        <use href="#tree2" x="330" y="388"/><use href="#tree1" x="335" y="393"/>

        <!-- 东翼花园/景观植被 -->
        <circle cx="365" cy="200" r="12" fill="rgba(80,140,68,0.07)"/>
        <circle cx="375" cy="380" r="13" fill="rgba(80,140,68,0.07)"/>
        <circle cx="355" cy="420" r="11" fill="rgba(80,140,68,0.06)"/>
        <use href="#tree2" x="362" y="202"/><use href="#tree2" x="370" y="195"/>
        <use href="#tree1" x="372" y="382"/><use href="#tree1" x="378" y="376"/>
        <use href="#tree3" x="352" y="422"/><use href="#tree2" x="360" y="418"/>

        <!-- 祥符禅寺古树林 -->
        <circle cx="235" cy="210" r="28" fill="rgba(75,140,65,0.15)"/>
        <circle cx="262" cy="205" r="25" fill="rgba(75,140,65,0.13)"/>
        <use href="#tree3" x="232" y="215"/><use href="#tree3" x="260" y="210"/>
        <use href="#tree1" x="240" y="208"/><use href="#tree1" x="252" y="202"/>
        <use href="#tree2" x="228" y="222"/><use href="#tree2" x="265" y="218"/>
        <use href="#tree2" x="245" y="220"/><use href="#tree3" x="255" y="216"/>
        <use href="#tree1" x="222" y="205"/><use href="#tree1" x="268" y="208"/>

        <!-- 山体植被 -->
        <ellipse cx="220" cy="55" rx="40" ry="22" fill="rgba(95,155,85,0.08)"/>
        <ellipse cx="150" cy="70" rx="35" ry="18" fill="rgba(95,155,85,0.06)"/>
        <ellipse cx="285" cy="58" rx="30" ry="16" fill="rgba(95,155,85,0.06)"/>

        <!-- L4: 广场/铺装 -->
        <ellipse cx="290" cy="715" rx="44" ry="11" fill="rgba(232,222,202,0.48)"
                 stroke="rgba(195,175,145,0.34)" stroke-width="1"/>
        <ellipse cx="274" cy="475" rx="38" ry="12" fill="rgba(225,215,190,0.42)"
                 stroke="rgba(195,175,145,0.28)" stroke-width="1"/>
        <ellipse cx="262" cy="353" rx="34" ry="10" fill="rgba(228,218,195,0.36)"
                 stroke="rgba(195,175,145,0.24)" stroke-width="0.9"/>
        <ellipse cx="248" cy="218" rx="30" ry="9" fill="rgba(228,218,195,0.32)"
                 stroke="rgba(195,175,145,0.22)" stroke-width="0.8"/>
        <ellipse cx="310" cy="400" rx="28" ry="8" fill="rgba(228,218,195,0.26)"
                 stroke="rgba(195,175,145,0.18)" stroke-width="0.8"/>

        <!-- L5: 游览路线 -->
        <!-- 中轴线主路 -->
        <path d="M290,738 L288,695 L286,658 L284,620 L280,566
                 L274,472 L268,408 L262,350 L256,305 L248,215 L238,48"
              fill="none" stroke="rgba(185,145,80,0.20)" stroke-width="10"
              stroke-linecap="round" stroke-linejoin="round"/>
        <path d="M290,738 L288,695 L286,658 L284,620 L280,566
                 L274,472 L268,408 L262,350 L256,305 L248,215 L238,48"
              fill="none" stroke="url(#routeGrad)" stroke-width="5.5"
              stroke-linecap="round" stroke-linejoin="round" opacity="0.72"/>
        <path d="M290,738 L288,695 L286,658 L284,620 L280,566
                 L274,472 L268,408 L262,350 L256,305 L248,215 L238,48"
              fill="none" stroke="#f8e080" stroke-width="2.2"
              stroke-dasharray="8,10" stroke-linecap="round" opacity="0.52"/>

        <!-- 东翼支线：九龙灌浴 → 曼飞龙塔 → 五印坛城 → 梵宫 -->
        <path d="M274,472 L310,415 L336,380 L340,278 L345,195" fill="none"
              stroke="rgba(185,145,80,0.16)" stroke-width="5.5" stroke-linecap="round"/>
        <path d="M274,472 L310,415 L336,380 L340,278 L345,195" fill="none"
              stroke="#d8a843" stroke-width="3.8"
              stroke-dasharray="6,6" stroke-linecap="round" opacity="0.56"/>

        <!-- 西侧支线：祥符禅寺 → 无尽意斋 -->
        <path d="M248,215 Q195,300 130,450 Q95,540 80,640" fill="none"
              stroke="rgba(185,145,80,0.14)" stroke-width="4.5"/>
        <path d="M248,215 Q195,300 130,450 Q95,540 80,640" fill="none"
              stroke="#d8a843" stroke-width="2.8"
              stroke-dasharray="5,5" stroke-linecap="round" opacity="0.48"/>

        <!-- 博览馆支线 -->
        <path d="M238,48 Q240,38 242,28" fill="none"
              stroke="#d8a843" stroke-width="2.5"
              stroke-dasharray="4,4" stroke-linecap="round" opacity="0.42"/>

        <!-- 登云道（祥符禅寺 → 大佛） -->
        <g opacity="0.50">
          <line x1="248" y1="215" x2="238" y2="48" stroke="#c49528" stroke-width="8" stroke-dasharray="2,8"/>
          <line x1="248" y1="198" x2="262" y2="198" stroke="#c49528" stroke-width="3"/>
          <line x1="246" y1="178" x2="260" y2="178" stroke="#c49528" stroke-width="3"/>
          <line x1="244" y1="158" x2="258" y2="158" stroke="#c49528" stroke-width="3"/>
          <line x1="242" y1="138" x2="256" y2="138" stroke="#c49528" stroke-width="3"/>
          <line x1="241" y1="118" x2="255" y2="118" stroke="#c49528" stroke-width="3"/>
          <line x1="240" y1="98" x2="254" y2="98" stroke="#c49528" stroke-width="3"/>
          <line x1="239" y1="78" x2="253" y2="78" stroke="#c49528" stroke-width="3"/>
          <line x1="238" y1="58" x2="252" y2="58" stroke="#c49528" stroke-width="3"/>
        </g>

        <!-- L6: 建筑插图 -->
        <!-- 灵山大佛（峰顶） -->
        <g transform="translate(238, 48)" filter="url(#shadow)">
          <circle cx="0" cy="4" r="18" fill="rgba(251,191,36,0.22)"/>
          <circle cx="0" cy="4" r="12" fill="rgba(251,191,36,0.12)"/>
          <rect x="-14" y="-9" width="28" height="20" rx="3.5" fill="#c89214"/>
          <rect x="-16" y="-10" width="32" height="5" rx="2.5" fill="#d4a01e"/>
          <rect x="-9" y="-18" width="18" height="12" rx="2.5" fill="#dcae28"/>
          <rect x="-4" y="-34" width="8" height="18" rx="4" fill="#e8bc38"/>
          <circle cx="0" cy="-38" r="5.5" fill="#f5cc48"/>
          <circle cx="0" cy="-33" r="12" fill="none" stroke="rgba(251,191,36,0.45)" stroke-width="2"/>
          <circle cx="0" cy="-33" r="16" fill="none" stroke="rgba(251,191,36,0.20)" stroke-width="1"/>
        </g>

        <!-- 祥符禅寺 -->
        <g transform="translate(248, 215)" filter="url(#shadow)">
          <rect x="-20" y="-14" width="40" height="18" rx="3" fill="#be7e4e"/>
          <path d="M-24,-14 Q-11,-25 0,-14 Q11,-25 24,-14" fill="#8b4513" opacity="0.78"/>
          <rect x="-9" y="-4" width="18" height="12" rx="2" fill="#cc9464" opacity="0.82"/>
          <rect x="-3.5" y="-21" width="7" height="9" rx="1.5" fill="#dcae28"/>
        </g>

        <!-- 灵山梵宫 -->
        <g transform="translate(345, 195)" filter="url(#shadow)">
          <rect x="-36" y="-12" width="72" height="20" rx="3" fill="#c8a070"/>
          <rect x="-30" y="-24" width="60" height="15" rx="3" fill="#d4b888"/>
          <ellipse cx="0" cy="-24" rx="22" ry="14" fill="#dcae28"/>
          <ellipse cx="0" cy="-24" rx="14" ry="9" fill="#ecc858" opacity="0.64"/>
          <rect x="-2.5" y="-36" width="5" height="13" rx="2" fill="#e8bc38"/>
          <circle cx="0" cy="-38" r="3.5" fill="#f8d468"/>
        </g>

        <!-- 五印坛城 -->
        <g transform="translate(340, 278)" filter="url(#shadowSm)">
          <rect x="-18" y="-7" width="36" height="12" rx="2.5" fill="#e8e4dc"/>
          <rect x="-14" y="-20" width="28" height="16" rx="2.5" fill="#f2eee6"/>
          <rect x="-14" y="-22" width="28" height="6" rx="1.5" fill="#cc4433" opacity="0.70"/>
          <polygon points="0,-30 -9,-18 9,-18" fill="#dcae28"/>
          <rect x="-2" y="-36" width="4" height="7" rx="1.5" fill="#e8bc38"/>
          <circle cx="0" cy="-38" r="3" fill="#f8d468"/>
        </g>

        <!-- 曼飞龙塔 -->
        <g transform="translate(336, 380)" filter="url(#shadowSm)">
          <ellipse cx="0" cy="0" rx="18" ry="5" fill="#e0dcd5"/>
          <path d="M-6,4 Q0,-14 6,4 Z" fill="#f0ece5"/>
          <circle cx="0" cy="-10" r="2.5" fill="#e8bc38"/>
          <path d="M-12,4 Q-10,-7 -8,4 Z" fill="#f0ece5" opacity="0.82"/>
          <path d="M 12,4 Q 10,-7  8,4 Z" fill="#f0ece5" opacity="0.82"/>
          <path d="M-8,4.5 Q-6,-6 -4,4.5 Z" fill="#f0ece5" opacity="0.74"/>
          <path d="M 8,4.5 Q 6,-6  4,4.5 Z" fill="#f0ece5" opacity="0.74"/>
        </g>

        <!-- 九龙灌浴 -->
        <g transform="translate(274, 472)">
          <ellipse cx="0" cy="0" rx="28" ry="9" fill="rgba(95,168,218,0.28)"
                   stroke="rgba(115,180,225,0.38)" stroke-width="1.4"/>
          <rect x="-5" y="-18" width="10" height="18" rx="2" fill="#cc9a10"/>
          <path d="M-10,-18 Q-16,-28 0,-32 Q16,-28 10,-18 Z" fill="#dcae28" opacity="0.78"/>
          <!-- 喷水 -->
          <line x1="-22" y1="-6" x2="-10" y2="-20" stroke="rgba(100,170,220,0.28)" stroke-width="1.2"/>
          <line x1="-18" y1="-1" x2="-7" y2="-22" stroke="rgba(100,170,220,0.24)" stroke-width="0.9"/>
          <line x1=" 22" y1="-6" x2=" 10" y2="-20" stroke="rgba(100,170,220,0.28)" stroke-width="1.2"/>
          <line x1=" 18" y1="-1" x2=" 7" y2="-22" stroke="rgba(100,170,220,0.24)" stroke-width="0.9"/>
          <line x1="0" y1="-32" x2="0" y2="-45" stroke="rgba(100,170,220,0.35)" stroke-width="1.5"/>
          <circle cx="0" cy="-48" r="3" fill="none" stroke="rgba(100,170,220,0.25)" stroke-width="0.8"/>
        </g>

        <!-- 降魔浮雕 -->
        <g transform="translate(268, 408)">
          <rect x="-28" y="-8" width="56" height="14" rx="2.5" fill="#c4a075"/>
          <rect x="-26" y="-6" width="52" height="10" rx="1.5" fill="#d8ba95" opacity="0.68"/>
          <line x1="-22" y1="-1" x2="22" y2="-1" stroke="rgba(145,100,48,0.28)" stroke-width="1.2"/>
          <line x1="-20" y1="2.5" x2="20" y2="2.5" stroke="rgba(145,100,48,0.18)" stroke-width="0.8"/>
        </g>

        <!-- 阿育王柱 -->
        <g transform="translate(262, 350)">
          <rect x="-6" y="-28" width="12" height="48" rx="2.5" fill="#d0c0a0"/>
          <rect x="-7" y="-28" width="14" height="6" rx="2" fill="#decbac"/>
          <circle cx="0" cy="-31" r="5" fill="#decbac"/>
        </g>

        <!-- 百子戏弥勒 -->
        <g transform="translate(256, 305)">
          <rect x="-24" y="-9" width="48" height="16" rx="2.5" fill="#a57e5c"/>
          <rect x="-22" y="-11" width="44" height="5" rx="2" fill="#bb9872"/>
          <path d="M-16,-11 Q-11,-22 -5,-15 Q2,-26 10,-17 Q15,-24 18,-11"
                fill="none" stroke="#dcae28" stroke-width="2.2" opacity="0.60"/>
        </g>

        <!-- 大照壁 -->
        <g transform="translate(290, 738)">
          <rect x="-36" y="-9" width="72" height="16" rx="2.5" fill="#d0c0a0"/>
          <rect x="-38" y="-8" width="76" height="12" rx="2" fill="#e4dccc" opacity="0.58"/>
          <line x1="-30" y1="0" x2="30" y2="0" stroke="rgba(145,100,48,0.22)" stroke-width="1.2"/>
        </g>

        <!-- 五明桥 -->
        <g transform="translate(288, 695)">
          <path d="M-38,5 Q-28,-12 -18,5 Q-9,-12 0,5 Q9,-12 18,5 Q28,-12 38,5"
                fill="none" stroke="#d0c0a0" stroke-width="6" stroke-linecap="round"/>
          <path d="M-40,8 L40,8" stroke="#bb9872" stroke-width="3.5" opacity="0.58" stroke-linecap="round"/>
        </g>

        <!-- 五智门 -->
        <g transform="translate(284, 620)">
          <rect x="-22" y="-7" width="44" height="9" rx="2" fill="#f0ece4"/>
          <rect x="-6" y="-23" width="12" height="18" rx="2" fill="#f0ece4"/>
          <rect x="-24" y="-17" width="48" height="3.5" rx="1.5" fill="#f2efe8"/>
          <rect x="-20" y="-21" width="40" height="3" rx="1.5" fill="#f2efe8"/>
        </g>

        <!-- 佛足坛 -->
        <g transform="translate(286, 658)">
          <rect x="-16" y="-9" width="32" height="13" rx="2.5" fill="#d4c5a8"/>
          <path d="M-19,-9 Q-10,-18 0,-9 Q10,-18 19,-9" fill="#bc9835" opacity="0.70"/>
          <circle cx="0" cy="-1" r="4.5" fill="rgba(205,155,85,0.38)"
                  stroke="rgba(185,135,65,0.35)" stroke-width="1.2"/>
        </g>

        <!-- 菩提大道 -->
        <g transform="translate(280, 566)" opacity="0.50">
          <rect x="-9" y="-3.5" width="18" height="7" rx="3.5" fill="#90785a"/>
        </g>

        <!-- 佛教文化博览馆 -->
        <g transform="translate(242, 28)">
          <rect x="-12" y="-5" width="24" height="10" rx="2" fill="#d4b888"/>
          <text x="0" y="1.5" text-anchor="middle" font-size="5.5" fill="#8b6914" font-weight="700">博览馆</text>
        </g>

        <!-- 无尽意斋 -->
        <g transform="translate(80, 640)" filter="url(#shadowSm)">
          <rect x="-15" y="-9" width="30" height="16" rx="2.5" fill="#d0c0a0"/>
          <rect x="-6" y="-5" width="12" height="8" rx="1.5" fill="rgba(195,175,152,0.38)"/>
          <path d="M-18,-9 Q0,-19 18,-9" fill="#8b6914" opacity="0.58"/>
        </g>

        <!-- L7: 区域标签 -->
        <g>
          <rect x="196" y="8" width="84" height="20" rx="10" fill="rgba(140,95,48,0.18)"/>
          <text x="238" y="21.5" text-anchor="middle" font-size="11" fill="rgba(140,95,48,0.60)" font-weight="700" letter-spacing="3" font-family="'KaiTi','STKaiti','SimSun',serif">峰 顶 区</text>

          <rect x="230" y="280" width="98" height="20" rx="10" fill="rgba(140,95,48,0.14)"/>
          <text x="279" y="293.5" text-anchor="middle" font-size="11" fill="rgba(140,95,48,0.52)" font-weight="700" letter-spacing="3" font-family="'KaiTi','STKaiti','SimSun',serif">核 心 朝 圣 区</text>

          <rect x="295" y="340" width="94" height="20" rx="10" fill="rgba(100,150,200,0.14)"/>
          <text x="342" y="353.5" text-anchor="middle" font-size="11" fill="rgba(80,130,180,0.52)" font-weight="700" letter-spacing="3" font-family="'KaiTi','STKaiti','SimSun',serif">佛教文化体验区</text>

          <rect x="215" y="185" width="82" height="20" rx="10" fill="rgba(140,95,48,0.14)"/>
          <text x="256" y="198.5" text-anchor="middle" font-size="11" fill="rgba(140,95,48,0.52)" font-weight="700" letter-spacing="3" font-family="'KaiTi','STKaiti','SimSun',serif">千年古刹区</text>

          <rect x="242" y="700" width="98" height="20" rx="10" fill="rgba(100,150,200,0.13)"/>
          <text x="291" y="713.5" text-anchor="middle" font-size="11" fill="rgba(80,130,180,0.52)" font-weight="700" letter-spacing="3" font-family="'KaiTi','STKaiti','SimSun',serif">入 口 广 场 区</text>

          <rect x="43" y="580" width="78" height="20" rx="10" fill="rgba(100,150,100,0.13)"/>
          <text x="82" y="593.5" text-anchor="middle" font-size="10" fill="rgba(80,130,90,0.48)" font-weight="700" letter-spacing="2" font-family="'KaiTi','STKaiti','SimSun',serif">山林静修区</text>
        </g>

        <!-- 指南针 -->
        <g transform="translate(395, 22)">
          <circle r="18" fill="rgba(255,255,255,0.65)" stroke="rgba(165,125,55,0.35)" stroke-width="1.4"/>
          <circle r="14" fill="none" stroke="rgba(165,125,55,0.15)" stroke-width="0.6"/>
          <path d="M0,-13 L5.5,0 L0,12 L-5.5,0 Z" fill="rgba(205,155,25,0.65)"/>
          <path d="M0,13 L4.5,0 L0,-12 L-4.5,0 Z" fill="rgba(215,200,175,0.55)"/>
          <text y="-11" text-anchor="middle" font-size="8" fill="rgba(205,155,25,0.75)" font-weight="900">N</text>
        </g>

        <!-- 入口标记 -->
        <g transform="translate(290, 748)">
          <circle r="5.5" fill="rgba(215,95,68,0.55)" stroke="rgba(215,95,68,0.75)" stroke-width="2.2"/>
          <text y="-8" text-anchor="middle" font-size="8" fill="rgba(195,80,55,0.65)" font-weight="700">入</text>
        </g>

        <!-- L8: 图例标题 -->
        <text x="210" y="-5" text-anchor="middle" font-size="14"
              fill="rgba(120,80,30,0.62)" font-weight="700" letter-spacing="5"
              font-family="'KaiTi','STKaiti','SimSun',serif">灵 山 胜 境 导 览 图</text>
        </g><!-- end translate(30,30) -->
      </svg>
    </div>

    <!-- Leaflet 地图容器 -->
    <div ref="leafletMap" class="leaflet-map"></div>

    <!-- 加载提示 -->
    <div v-if="!mapReady" class="map-loading">
      <span class="loading-spin">⟳</span>
      <span>地图加载中...</span>
    </div>

    <!-- 缩放控件 -->
    <div class="zoom-controls">
      <button class="zoom-btn" @click.stop="zoomIn" title="放大">＋</button>
      <span class="zoom-level">{{ zoomPercent }}%</span>
      <button class="zoom-btn" @click.stop="zoomOut" title="缩小">－</button>
      <button class="zoom-btn zoom-reset" @click.stop="resetZoom" title="重置">⟳</button>
      <button class="zoom-btn zoom-fullscreen" @click.stop="toggleFullscreen" :title="isFullscreen ? '退出全屏' : '全屏'">
        {{ isFullscreen ? '✕' : '⛶' }}
      </button>
    </div>

    <!-- 图例 -->
    <div class="map-legend">
      <div class="legend-item"><span class="legend-dot core"></span>核心地标</div>
      <div class="legend-item"><span class="legend-dot temple"></span>寺院宗教</div>
      <div class="legend-item"><span class="legend-dot culture"></span>文化艺术</div>
      <div class="legend-item"><span class="legend-dot general"></span>其他景点</div>
      <div class="legend-item"><span class="legend-line main"></span>中轴线</div>
      <div class="legend-item"><span class="legend-line branch"></span>支线</div>
    </div>

    <!-- Leaflet 版本标识（确认新版本已加载）-->
    <div v-if="mapReady" class="leaflet-badge">🗺️ Leaflet</div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

defineOptions({ name: 'Scenic2DMap' })

const props = defineProps({
  spots: { type: Array, default: () => [] },
  currentSpot: { type: String, default: '' }
})

const emit = defineEmits(['spotClick'])

// ===== 状态 =====
const mapRoot = ref(null)
const svgSource = ref(null)
const leafletMap = ref(null)
const mapReady = ref(false)
const currentZoom = ref(0)
const isFullscreen = ref(false)

// Leaflet 实例
let map = null
let imageOverlay = null
let markers = {}
let imgBounds = [[0, 0], [840, 480]]  // 动态更新
const VIEWBOX = { x: -30, y: -30, w: 480, h: 840 }

// ===== 缩放百分比 =====
const zoomPercent = computed(() => {
  if (!map) return 100
  return Math.round((map.getZoom() - map.getMinZoom()) / (map.getMaxZoom() - map.getMinZoom()) * 200)
})

// ===== 分类样式 =====
function getCategoryStyle(category) {
  const map = {
    '核心地标':   { cls: 'core',    color: '#c8960c' },
    '寺院':       { cls: 'temple',  color: '#b07040' },
    '艺术殿堂':   { cls: 'culture', color: '#a855f7' },
    '藏传佛教':   { cls: 'culture', color: '#8b5cf6' },
    '南传佛教':   { cls: 'culture', color: '#8b5cf6' },
    '博览馆':     { cls: 'temple',  color: '#b07040' },
    '入口':       { cls: 'general', color: '#4a8c5c' },
    '门户':       { cls: 'general', color: '#4a8c5c' },
    '桥梁':       { cls: 'general', color: '#4a8c5c' },
    '朝圣':       { cls: 'general', color: '#4a8c5c' },
    '步道':       { cls: 'general', color: '#4a8c5c' },
    '动态景观':   { cls: 'core',    color: '#c8960c' },
    '浮雕':       { cls: 'general', color: '#4a8c5c' },
    '地标':       { cls: 'temple',  color: '#b07040' },
    '祈福':       { cls: 'general', color: '#4a8c5c' },
    '名人纪念馆': { cls: 'general', color: '#4a8c5c' }
  }
  return map[category] || { cls: 'general', color: '#4a8c5c' }
}

// ===== 创建 DivIcon =====
function createDivIcon(spot) {
  const cat = getCategoryStyle(spot.category)
  return L.divIcon({
    className: `leaflet-spot-marker marker-cat-${cat.cls}`,
    html: `<div class="marker-bubble"><span class="marker-emoji">${spot.icon}</span></div>
           <div class="marker-stem"></div>
           <div class="marker-name">${spot.name}</div>`,
    iconSize: [64, 74],
    iconAnchor: [32, 74],
    popupAnchor: [0, -68]
  })
}

// ===== 创建 Popup 内容 =====
function createPopupHtml(spot) {
  const desc = (spot.description || '').length > 100
    ? spot.description.slice(0, 100) + '...'
    : (spot.description || '')
  return `
    <div class="slp-wrap">
      <div class="slp-header">
        <span class="slp-icon">${spot.icon}</span>
        <span class="slp-name">${spot.name}</span>
      </div>
      <p class="slp-desc">${desc}</p>
      <div class="slp-meta">
        <span>🕐 ${spot.openTime || '—'}</span>
        <span>💰 ${spot.price || '—'}</span>
      </div>
      <div class="slp-tip">👆 点击标记开始AI讲解</div>
    </div>
  `
}

// ===== 坐标转换：spot.mapX/mapY → Leaflet像素坐标 =====
function spotToLeaflet(spot) {
  const px = (spot.mapX - VIEWBOX.x) / VIEWBOX.w * imgBounds[1][1]
  const py = (spot.mapY - VIEWBOX.y) / VIEWBOX.h * imgBounds[1][0]
  return [py, px]  // Leaflet: [y, x]
}

// ===== 等待容器有有效尺寸 =====
function waitForContainerSize(el, timeout = 2000) {
  return new Promise((resolve, reject) => {
    const start = Date.now()
    function check() {
      const w = el.clientWidth
      const h = el.clientHeight
      if (w > 10 && h > 10) {
        console.log('[Scenic2DMap] Container ready:', w, 'x', h)
        resolve({ w, h })
        return
      }
      if (Date.now() - start > timeout) {
        reject(new Error('Container size timeout'))
        return
      }
      requestAnimationFrame(check)
    }
    check()
  })
}

// ===== 初始化 Leaflet 地图 =====
async function initMap() {
  await nextTick()

  // 1. 序列化 SVG → Blob URL
  const svgEl = svgSource.value?.querySelector('svg')
  if (!svgEl || !leafletMap.value) {
    console.warn('[Scenic2DMap] SVG or map container not found')
    return
  }

  let imgUrl = ''
  try {
    const svgStr = new XMLSerializer().serializeToString(svgEl)
    const blob = new Blob([svgStr], { type: 'image/svg+xml' })
    imgUrl = URL.createObjectURL(blob)
    console.log('[Scenic2DMap] SVG serialized, blob size:', blob.size)
  } catch (err) {
    console.error('[Scenic2DMap] SVG serialization failed:', err)
    return
  }

  // 2. 加载 Image 获取实际尺寸
  const img = new Image()
  try {
    await new Promise((resolve, reject) => {
      img.onload = resolve
      img.onerror = () => reject(new Error('SVG image load failed'))
      img.src = imgUrl
    })
    console.log('[Scenic2DMap] Image loaded:', img.naturalWidth, 'x', img.naturalHeight)
  } catch (err) {
    console.error('[Scenic2DMap] Image load failed:', err)
    URL.revokeObjectURL(imgUrl)
    return
  }

  // 3. 等待 Leaflet 容器有有效尺寸（关键修复：避免 0 尺寸初始化导致 fitBounds 失效）
  let containerW, containerH
  try {
    const size = await waitForContainerSize(leafletMap.value)
    containerW = size.w
    containerH = size.h
  } catch {
    containerW = leafletMap.value.clientWidth || 400
    containerH = leafletMap.value.clientHeight || 600
  }

  // 4. 创建 Leaflet 地图
  try {
    map = L.map(leafletMap.value, {
      crs: L.CRS.Simple,
      minZoom: -3,
      maxZoom: 4,
      zoomSnap: 0.1,
      attributionControl: false,
      zoomControl: false,
      doubleClickZoom: true,
      scrollWheelZoom: true,
      dragging: true,
      worldCopyJump: false
    })

    // 使用实际图片尺寸更新 bounds
    const imgW = img.naturalWidth
    const imgH = img.naturalHeight
    imgBounds = [[0, 0], [imgH, imgW]]
    console.log('[Scenic2DMap] Creating imageOverlay with bounds:', imgBounds)
    imageOverlay = L.imageOverlay(imgUrl, imgBounds).addTo(map)

    // 【关键修复】手动计算合适的缩放级别，而不是用 fitBounds
    // CRS.Simple 中 zoom=0 表示 1 坐标单位 = 1 像素
    // 需要缩放到能完整显示图片
    const scaleX = (containerW - 20) / imgW   // 留 20px 边距
    const scaleY = (containerH - 20) / imgH
    const fitScale = Math.min(scaleX, scaleY)
    const fitZoom = Math.log2(fitScale)
    // 限制在 minZoom 和 maxZoom 之间
    const clampedZoom = Math.max(-3, Math.min(4, fitZoom))
    const centerY = imgH / 2
    const centerX = imgW / 2
    console.log('[Scenic2DMap] Fit: container=%dx%d img=%dx%d scale=%.3f zoom=%.2f clamped=%.2f',
      containerW, containerH, imgW, imgH, fitScale, fitZoom, clampedZoom)
    map.setView([centerY, centerX], clampedZoom)
    currentZoom.value = map.getZoom()

    // 监听缩放
    map.on('zoom', () => { currentZoom.value = map.getZoom() })

    // 5. 添加景点标记
    placeMarkers()

    // 6. 初始选中
    if (props.currentSpot) {
      focusSpotByName(props.currentSpot)
    }

    mapReady.value = true
    console.log('[Scenic2DMap] Leaflet map ready, markers:', Object.keys(markers).length)

    // 延迟再次校准（面板展开动画可能还在进行，等动画结束再校一次）
    const delayedRecenter = (delay) => {
      setTimeout(() => {
        if (!map || !leafletMap.value) return
        map.invalidateSize()
        const z = calcFitZoom()
        const cz = Math.max(-3, Math.min(4, z))
        if (cz > -10) {
          const ih = imgBounds[1][0]
          const iw = imgBounds[1][1]
          map.setView([ih / 2, iw / 2], cz, { animate: false })
          currentZoom.value = map.getZoom()
        }
        console.log('[Scenic2DMap] Delayed recenter at zoom:', cz?.toFixed(2))
      }, delay)
    }
    delayedRecenter(200)
    delayedRecenter(500)
  } catch (err) {
    console.error('[Scenic2DMap] Leaflet init failed:', err)
    URL.revokeObjectURL(imgUrl)
  }
}

// ===== 放置标记 =====
function placeMarkers() {
  if (!map) return
  Object.values(markers).forEach(m => map.removeLayer(m))
  markers = {}

  props.spots.forEach(spot => {
    if (spot.mapX == null || spot.mapY == null) return

    const marker = L.marker(spotToLeaflet(spot), {
      icon: createDivIcon(spot),
      interactive: true,
      riseOnHover: true
    })

    marker.bindPopup(createPopupHtml(spot), {
      className: 'spot-leaflet-popup',
      closeButton: true,
      maxWidth: 260
    })

    marker.on('click', () => {
      emit('spotClick', spot)
    })

    marker.addTo(map)
    markers[spot.id] = marker
  })
}

// ===== 聚焦景点 =====
function focusSpotByName(name) {
  if (!map) return
  const spot = props.spots.find(s => s.name === name)
  if (spot && markers[spot.id]) {
    const latlng = spotToLeaflet(spot)
    map.panTo(latlng, { animate: true, duration: 0.3 })
    markers[spot.id].openPopup()
  }
}

// ===== 缩放控制 =====
function zoomIn() {
  if (map) map.zoomIn()
}

function zoomOut() {
  if (map) map.zoomOut()
}

function calcFitZoom() {
  if (!leafletMap.value) return -1
  const w = leafletMap.value.clientWidth
  const h = leafletMap.value.clientHeight
  const imgW = imgBounds[1][1]
  const imgH = imgBounds[1][0]
  const scaleX = (w - 20) / imgW
  const scaleY = (h - 20) / imgH
  return Math.log2(Math.min(scaleX, scaleY))
}

function resetZoom() {
  if (!map) return
  const zoom = calcFitZoom()
  const clamped = Math.max(-3, Math.min(4, zoom))
  const imgH = imgBounds[1][0]
  const imgW = imgBounds[1][1]
  map.setView([imgH / 2, imgW / 2], clamped, { animate: true })
}

function toggleFullscreen() {
  isFullscreen.value = !isFullscreen.value
  const root = mapRoot.value
  if (!root) return
  if (isFullscreen.value) {
    root.classList.add('is-fullscreen')
  } else {
    root.classList.remove('is-fullscreen')
  }
  // 延迟让 CSS transition 生效后再刷新 Leaflet 尺寸
  setTimeout(() => {
    map?.invalidateSize()
    const zoom = calcFitZoom()
    const clamped = Math.max(-3, Math.min(4, zoom))
    if (clamped > -10) {
      const imgH = imgBounds[1][0]
      const imgW = imgBounds[1][1]
      map?.setView([imgH / 2, imgW / 2], clamped, { animate: true })
    }
  }, 350)
}

// ===== 监听当前景点变化 =====
watch(() => props.currentSpot, (name) => {
  if (name && mapReady.value) {
    focusSpotByName(name)
  }
})

// ===== 监听 spots 变化（数据加载后重新放置标记）=====
watch(() => props.spots, (newSpots) => {
  if (newSpots.length > 0 && mapReady.value) {
    placeMarkers()
  }
}, { deep: true })

// ===== 处理窗口 resize =====
function onResize() {
  if (map) {
    map.invalidateSize()
    const zoom = calcFitZoom()
    const clamped = Math.max(-3, Math.min(4, zoom))
    if (clamped > -10) {
      const imgH = imgBounds[1][0]
      const imgW = imgBounds[1][1]
      map.setView([imgH / 2, imgW / 2], clamped)
    }
  }
}

// ResizeObserver
let resizeObserver = null
let _initInProgress = false

// ===== 生命周期 =====
onMounted(() => {
  // 使用 ResizeObserver：当容器获得有效尺寸时自动初始化
  if (leafletMap.value) {
    resizeObserver = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const w = entry.contentRect.width
        const h = entry.contentRect.height
        if (w > 10 && h > 10) {
          if (!map && !_initInProgress) {
            console.log('[Scenic2DMap] ResizeObserver: container got size, init map')
            _initInProgress = true
            initMap().finally(() => { _initInProgress = false })
          } else if (map) {
            // 【关键修复】容器尺寸变化后，重新计算合适的缩放并居中
            map.invalidateSize()
            const zoom = calcFitZoom()
            const clamped = Math.max(-3, Math.min(4, zoom))
            if (clamped > -10) {
              const imgH = imgBounds[1][0]
              const imgW = imgBounds[1][1]
              // 只在非用户交互时自动调整（避免干扰用户手动缩放）
              if (!map._userInteracting) {
                map.setView([imgH / 2, imgW / 2], clamped, { animate: false })
              }
            }
          }
        }
      }
    })
    resizeObserver.observe(leafletMap.value)
  }
  // 降级：如果 500ms 后还没初始化，强制启动
  setTimeout(() => {
    if (!map && !_initInProgress) {
      console.log('[Scenic2DMap] Fallback init after 500ms')
      _initInProgress = true
      initMap().finally(() => { _initInProgress = false })
    }
  }, 500)
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  }
  if (map) {
    map.remove()
    map = null
  }
})
</script>

<style scoped>
.scenic-2d-map {
  position: relative;
  width: 100%;
  height: 100%;
  border-radius: 14px;
  overflow: hidden;
  background: #ede4d3;
}

/* ===== 隐藏的 SVG 渲染源（opacity:0 确保浏览器渲染）===== */
.svg-source {
  position: absolute;
  left: 0;
  top: 0;
  width: 960px;
  height: 1680px;
  opacity: 0;
  pointer-events: none;
  z-index: -1;
}

/* ===== Leaflet 地图容器 ===== */
.leaflet-map {
  width: 100%;
  height: 100%;
  z-index: 1;
}

/* ===== Leaflet 覆盖样式 ===== */
:deep(.leaflet-container) {
  background: transparent !important;
}

:deep(.leaflet-control-attribution) {
  display: none !important;
}

/* ===== Leaflet Popup ===== */
:deep(.spot-leaflet-popup .leaflet-popup-content-wrapper) {
  background: rgba(20, 30, 50, 0.96);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(251, 191, 36, 0.35);
  border-radius: 14px;
  color: #e2e8f0;
  box-shadow: 0 12px 40px rgba(0,0,0,0.45);
}

:deep(.spot-leaflet-popup .leaflet-popup-content) {
  margin: 14px 16px;
  font-size: 13px;
  line-height: 1.5;
}

:deep(.spot-leaflet-popup .leaflet-popup-tip) {
  background: rgba(20, 30, 50, 0.96);
  border: 1px solid rgba(251, 191, 36, 0.35);
}

:deep(.spot-leaflet-popup .leaflet-popup-close-button) {
  color: #94a3b8 !important;
  font-size: 20px !important;
  padding: 6px 8px 0 0 !important;
}

:deep(.spot-leaflet-popup .leaflet-popup-close-button:hover) {
  color: #e2e8f0 !important;
}

.slp-wrap {
  min-width: 220px;
}

.slp-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.slp-icon {
  font-size: 24px;
}

.slp-name {
  font-size: 16px;
  font-weight: 700;
  color: #fbbf24;
}

.slp-desc {
  font-size: 12px;
  line-height: 1.7;
  color: #cbd5e1;
  margin: 0 0 8px 0;
}

.slp-meta {
  display: flex;
  gap: 14px;
  font-size: 11.5px;
  color: #94a3b8;
  margin-bottom: 6px;
}

.slp-tip {
  font-size: 11px;
  color: #f59e0b;
  opacity: 0.8;
  text-align: center;
  margin-top: 4px;
}

/* ===== Leaflet 标记样式 ===== */
:deep(.leaflet-spot-marker) {
  background: transparent !important;
  border: none !important;
  text-align: center;
}

:deep(.leaflet-spot-marker .marker-bubble) {
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  margin: 0 auto;
  box-shadow: 0 2px 6px rgba(0,0,0,0.22);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

:deep(.leaflet-spot-marker:hover .marker-bubble) {
  transform: scale(1.15);
}

:deep(.leaflet-spot-marker .marker-emoji) {
  font-size: 20px;
  line-height: 1;
}

:deep(.leaflet-spot-marker .marker-stem) {
  width: 3px;
  height: 8px;
  opacity: 0.40;
  margin: 0 auto;
}

:deep(.leaflet-spot-marker .marker-name) {
  font-size: 10px;
  white-space: nowrap;
  margin-top: 3px;
  padding: 3px 8px;
  border-radius: 5px;
  background: rgba(255,255,255,0.82);
  color: #5c3e20;
  letter-spacing: 0.5px;
  font-weight: 700;
  display: inline-block;
}

/* 分类颜色 */
:deep(.marker-cat-core .marker-bubble) {
  width: 46px; height: 46px;
  background: radial-gradient(circle at 38% 38%, #f5d060, #c8960c);
  box-shadow: 0 0 14px rgba(200,150,12,0.45);
}
:deep(.marker-cat-core .marker-stem) { background: #c8960c; }

:deep(.marker-cat-temple .marker-bubble) {
  width: 42px; height: 42px;
  background: radial-gradient(circle at 38% 38%, #e8b870, #b07040);
  box-shadow: 0 0 12px rgba(176,112,64,0.40);
}
:deep(.marker-cat-temple .marker-stem) { background: #b07040; }

:deep(.marker-cat-culture .marker-bubble) {
  width: 43px; height: 43px;
  background: radial-gradient(circle at 38% 38%, #d8b4fe, #8b5cf6);
  box-shadow: 0 0 12px rgba(139,92,246,0.40);
}
:deep(.marker-cat-culture .marker-stem) { background: #8b5cf6; }

:deep(.marker-cat-general .marker-bubble) {
  width: 38px; height: 38px;
  background: radial-gradient(circle at 38% 38%, #6dc580, #3a7d4a);
  box-shadow: 0 0 10px rgba(58,125,74,0.40);
}
:deep(.marker-cat-general .marker-stem) { background: #3a7d4a; }

/* ===== 加载提示 ===== */
.map-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #8b7355;
  font-size: 14px;
  z-index: 5;
  background: #ede4d3;
}

.loading-spin {
  font-size: 28px;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

/* ===== 缩放控件 ===== */
.zoom-controls {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(8px);
  border-radius: 12px;
  border: 1px solid rgba(160,140,110,0.25);
  padding: 6px 5px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.14);
}

.zoom-btn {
  width: 34px;
  height: 34px;
  border: none;
  background: rgba(180,150,120,0.12);
  color: #5c3e20;
  border-radius: 8px;
  font-size: 20px;
  cursor: pointer;
  transition: background 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  line-height: 1;
}

.zoom-btn:hover {
  background: rgba(180,150,120,0.28);
}

.zoom-reset {
  font-size: 16px;
  margin-top: 2px;
  border-top: 1px solid rgba(160,140,110,0.18);
  padding-top: 5px;
  border-radius: 0 0 8px 8px;
}

.zoom-level {
  font-size: 11px;
  color: #8b7355;
  font-weight: 700;
  padding: 2px 0;
}

/* ===== 图例 ===== */
.map-legend {
  position: absolute;
  bottom: 10px;
  left: 10px;
  z-index: 1000;
  background: rgba(255,255,255,0.92);
  backdrop-filter: blur(8px);
  border-radius: 12px;
  border: 1px solid rgba(160,140,110,0.25);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  font-size: 12px;
  color: #5c3e20;
  font-weight: 600;
  box-shadow: 0 2px 12px rgba(0,0,0,0.14);
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.legend-dot {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  flex-shrink: 0;
}
.legend-dot.core    { background: radial-gradient(circle at 35% 35%, #f5d060, #c8960c); }
.legend-dot.temple  { background: radial-gradient(circle at 35% 35%, #e8b870, #b07040); }
.legend-dot.culture { background: radial-gradient(circle at 35% 35%, #d8b4fe, #8b5cf6); }
.legend-dot.general { background: radial-gradient(circle at 35% 35%, #6dc580, #3a7d4a); }

.legend-line {
  width: 18px;
  height: 3.5px;
  border-radius: 2px;
  flex-shrink: 0;
}
.legend-line.main   { background: #c8960c; opacity: 0.65; }
.legend-line.branch {
  background-image: repeating-linear-gradient(90deg, #d4a843 0, #d4a843 4px, transparent 4px, transparent 7px);
  opacity: 0.50;
}

/* ===== 响应式 ===== */
@media (max-width: 480px) {
  .zoom-controls { top: 6px; right: 6px; padding: 5px 4px; }
  .zoom-btn { width: 30px; height: 30px; font-size: 17px; }
  .zoom-reset { font-size: 14px; }
  .map-legend { bottom: 6px; left: 6px; padding: 7px 10px; font-size: 10px; }
  .legend-dot { width: 13px; height: 13px; }
}

/* Leaflet 版本标识（低调）*/
.leaflet-badge {
  position: absolute;
  bottom: 10px;
  right: 10px;
  z-index: 1000;
  background: rgba(30,40,60,0.55);
  color: rgba(255,255,255,0.55);
  font-size: 9px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 500;
  letter-spacing: 0.5px;
  pointer-events: none;
}

/* ===== 全屏模式 ===== */
.scenic-2d-map.is-fullscreen {
  position: fixed !important;
  inset: 0 !important;
  z-index: 9999 !important;
  border-radius: 0 !important;
}

.zoom-fullscreen {
  font-size: 16px !important;
}
</style>

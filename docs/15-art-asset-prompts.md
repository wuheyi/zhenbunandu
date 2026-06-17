# 美术素材提示词

本文记录《朕不南渡》首发素材清单和逐项画图提示词。目标是让后续批量生成图片时保持统一的北宋视觉风格，并避免每张图临时发挥导致美术方向散掉。

## 通用规范

### 统一风格

所有素材优先使用以下风格：

```text
Northern Song dynasty historical strategy game art, refined Chinese court painting, silk handscroll texture, restrained ink lines, mineral green and cinnabar accents, warm aged parchment, cinematic but not fantasy, historically grounded, elegant composition, no modern objects, no readable text, no watermark
```

### 通用反向提示

生成时建议追加：

```text
Negative prompt: modern clothing, modern buildings, neon colors, fantasy armor, exaggerated weapons, anime style, western medieval castle, Qing dynasty queue hairstyle, Ming dynasty winged hat, readable text, logo, watermark, blurry face, extra fingers, distorted hands, low quality
```

### 文字处理

所有图片不要生成可读文字。奏疏、牌匾、印章上的文字由前端叠加。

### 文件命名

建议：

```text
art/<category>/<asset_id>.png
```

人物立绘建议：

```text
art/characters/char_li_gang.png
```

## 地图与场景底图

### map_north_china_strategy

用途：主界面北方战略舆图。

建议尺寸：2048x1280。

Prompt:

```text
Northern Song dynasty strategic map of northern China centered on Bianjing Kaifeng, the Yellow River, Hedong, Hebei, Shaanxi and Huainan, painted as an antique silk military map, delicate ink linework, muted mineral green rivers, warm parchment background, blank cartouches with no readable text, subtle route spaces for UI overlays, elegant Song dynasty court painting style, top-down handscroll composition, no modern borders, no labels, no watermark
```

### map_bianjing_city_defense

用途：汴京城防视图。

建议尺寸：2048x1280。

Prompt:

```text
Top-down stylized defense map of Northern Song capital Bianjing Kaifeng, square city walls, gates, imperial palace area, river gates, granaries and defensive districts, antique silk map style, fine ink outlines, muted cinnabar risk accents, empty spaces for UI markers, historically grounded Song dynasty city planning, no readable labels, no modern elements, no watermark
```

### map_grain_logistics

用途：粮运财税图层底图。

建议尺寸：2048x1280。

Prompt:

```text
Ancient Chinese logistics map for Northern Song grain transport, river routes, canal bends, warehouses, boats, relay stations and roads leading toward Bianjing, painted on aged parchment silk, fine ink and pale blue-green water, understated cinnabar route markers without text, clean areas for interface overlays, historical strategy game UI background, no readable text, no watermark
```

### map_siege_overview

用途：围城阶段金军营地与汴京外围。

建议尺寸：2048x1280。

Prompt:

```text
Wide tactical siege overview of Bianjing during the Jingkang crisis, city walls in the lower center, enemy camps outside the walls, river and roads around the city, winter haze, restrained historical Chinese handscroll painting, ink lines with muted cinnabar danger accents, empty UI-safe zones, no gore, no readable text, no modern elements
```

### map_hebei_hedong_front

用途：河北河东战线详情。

建议尺寸：2048x1280。

Prompt:

```text
Northern Song frontier campaign map showing Hebei and Hedong mountain passes, fortified towns, river crossings and military roads, antique Song dynasty military atlas style, fine ink linework, mineral green hills, warm parchment, no labels or readable text, clean overlay-ready composition, historically grounded
```

### map_qinwang_routes

用途：勤王路线视图。

建议尺寸：2048x1280。

Prompt:

```text
Antique Chinese route map showing relief armies marching toward Bianjing from Shaanxi, Hedong, Huainan and Jiangnan, subtle roads, river crossings, supply depots and danger zones, Song dynasty silk handscroll style, soft ink wash, restrained cinnabar and teal route accents, no readable text, no modern symbols
```

### map_faction_influence

用途：派系势力图背景。

建议尺寸：2048x1280。

Prompt:

```text
Abstract political influence map of a Northern Song imperial court and capital bureaucracy, palace halls, ministries, granaries, military camps and scholar academies arranged like a hand-drawn network on parchment, elegant ink lines, muted colored seals as empty nodes, no readable text, no faces, no modern diagram style
```

### bg_imperial_desk

用途：主界面御案背景。

建议尺寸：2048x1280。

Prompt:

```text
Northern Song emperor's desk viewed from above, aged wooden table, layered memorial papers, blank silk scrolls, cinnabar seal paste, brush rest, inkstone, subtle warm candlelight, refined historical realism mixed with Chinese painting texture, no readable text, no modern objects, clean UI-safe center area
```

## UI 纹理与组件素材

### ui_parchment_base

用途：通用面板底纹。

建议尺寸：1024x1024，可平铺。

Prompt:

```text
Seamless warm aged parchment texture inspired by Song dynasty paper and silk, subtle fibers, gentle uneven edges, very low contrast, no stains shaped like text, no symbols, no border, suitable for strategy game UI panels
```

### ui_silk_panel

用途：高级弹层和月末报告底。

建议尺寸：1024x1024，可平铺。

Prompt:

```text
Seamless pale silk texture for Northern Song court UI, fine woven fibers, warm ivory tone, subtle mineral pigment speckles, elegant and restrained, no text, no pattern that distracts, no watermark
```

### ui_memorial_sheet

用途：奏疏卡片。

建议尺寸：1024x1536。

Prompt:

```text
Blank Northern Song memorial paper sheet, vertical folded document on warm parchment, faint ruled margins, slightly worn edges, elegant court stationery, no readable text, no seal, centered and isolated for UI use
```

### ui_edict_scroll

用途：拟旨和颁诏界面。

建议尺寸：1536x1024。

Prompt:

```text
Blank imperial edict scroll from the Northern Song dynasty, horizontal silk scroll with ornate but restrained borders, warm ivory silk, cinnabar seal area left empty, no readable text, no dragon fantasy, elegant historical court style
```

### ui_ledger_page

用途：账册和财政流水。

建议尺寸：1024x1536。

Prompt:

```text
Blank ancient Chinese accounting ledger page from Northern Song bureaucracy, ruled columns without readable writing, worn paper, muted ink guidelines, official archive feeling, no text, no numbers, no modern grid, suitable for UI overlay
```

### ui_secret_letter

用途：密札、密令面板。

建议尺寸：1024x1024。

Prompt:

```text
Folded secret letter on aged Song dynasty paper, blank surface, small tie cord, subtle shadow, tense imperial intelligence atmosphere, no readable text, no symbols, isolated on transparent-feeling warm background
```

### ui_evidence_slip

用途：证据条、摘录卡。

建议尺寸：768x512。

Prompt:

```text
Small blank evidence slip made of aged Chinese paper, torn archive edge, faint ink smudge, no readable text, no seal, designed for historical strategy game UI, clean centered object
```

### ui_cinnabar_seal_blank

用途：确认、裁断、颁诏印章。

建议尺寸：512x512，透明背景后处理。

Prompt:

```text
Blank cinnabar imperial seal mark, square red stamp impression on transparent-style background, rough carved edges, no readable characters, no logo, authentic Chinese seal texture, high contrast for UI button overlay
```

### ui_danger_stamp_blank

用途：危、急、疑状态印章底。

建议尺寸：512x512，透明背景后处理。

Prompt:

```text
Round cinnabar warning stamp mark for historical Chinese strategy game UI, rough ink seal texture, empty center with no readable text, transparent-style background, dramatic but restrained
```

### ui_wooden_command_bar

用途：底部御案操作栏。

建议尺寸：2048x256。

Prompt:

```text
Long carved dark wood command bar inspired by Northern Song imperial desk furniture, subtle lacquer sheen, restrained carved borders, warm shadows, no text, no icons, flat front-facing UI asset
```

### ui_court_nameplate

用途：朝臣席姓名牌。

建议尺寸：768x256。

Prompt:

```text
Blank Song dynasty court nameplate, small dark lacquer plaque with warm aged paper inset, subtle cinnabar corner mark, no text, no modern shape, clean UI component on transparent-style background
```

### ui_report_header

用途：月末报告标题底。

建议尺寸：1536x384。

Prompt:

```text
Elegant blank header banner for a Northern Song monthly court report, pale silk, faint ink mountain pattern, cinnabar border accents, no readable text, no logo, wide UI component
```

### ui_map_marker_gate

用途：城门地图节点。

建议尺寸：256x256，透明背景后处理。

Prompt:

```text
Small icon of an ancient Chinese city gate for a historical strategy map, Northern Song style, ink line and muted cinnabar roof accents, no text, transparent-style background, readable at small size
```

### ui_map_marker_army

用途：军队地图节点。

建议尺寸：256x256，透明背景后处理。

Prompt:

```text
Small historical strategy map icon of a Song dynasty army camp banner, ink linework, muted cinnabar and dark wood colors, no readable text, transparent-style background, simple silhouette readable at small size
```

### ui_map_marker_grain

用途：粮仓和粮船节点。

建议尺寸：256x256，透明背景后处理。

Prompt:

```text
Small map icon of an ancient Chinese granary and grain sack, Northern Song style, fine ink lines, muted wheat and parchment colors, no text, transparent-style background, clear at small size
```

### ui_map_marker_intel

用途：密令、情报节点。

建议尺寸：256x256，透明背景后处理。

Prompt:

```text
Small map icon of a sealed secret letter and ink brush, historical Chinese intelligence motif, restrained black ink and cinnabar, no text, transparent-style background, clean strategy UI icon
```

## 主要人物立绘

人物立绘统一要求：半身像，朝堂纸绢背景，方便裁成卡片。不要生成文字。

### char_song_qinzong

用途：玩家皇帝形象、菜单和结局。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a young Northern Song emperor during the Jingkang crisis, wearing historically grounded imperial court robes and black futou-style headwear, anxious but resolute expression, refined Chinese court painting style with subtle realistic detail, warm silk background, no text, no crown fantasy, no modern elements
```

### char_li_gang

用途：主战守城核心。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of Li Gang as a resolute Northern Song statesman, middle-aged scholar official in Song dynasty court robes and black futou hat, stern eyes, holding a blank memorial tablet, loyal and courageous atmosphere, refined Chinese historical portrait, silk background, no readable text
```

### char_zhong_shidao

用途：西军老将。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of an elderly Northern Song frontier general inspired by Zhong Shidao, weathered face, Song military robe with practical armor under official cloak, calm veteran authority, muted winter frontier colors, refined historical painting, no readable text, no fantasy armor
```

### char_zong_ze

用途：勤王和中兴路线核心。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of Zong Ze as a determined Northern Song official-general, older scholar warrior, austere court robe, strong gaze, subtle battlefield map in the background without labels, historical Chinese portrait style, warm parchment and ink tones, no text
```

### char_peace_chancellor

用途：主和宰执代表。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a cautious Northern Song chancellor advocating negotiation, senior scholar official in elegant dark court robes and futou hat, worried expression, refined but evasive posture, palace interior silk background, historically grounded, no readable text
```

### char_finance_minister

用途：户部尚书。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song finance minister, thin scholar official in formal robes, holding a blank ledger, calculating and exhausted expression, archive shelves blurred behind him, refined Song court painting style, no readable text, no modern objects
```

### char_kaifeng_prefect

用途：开封府尹。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of the prefect of Kaifeng during a wartime crisis, Northern Song official robe, firm practical expression, city gate and busy capital street suggested in the background, refined Chinese historical portrait, warm parchment tones, no text
```

### char_imperial_city司_chief

用途：皇城司密探首领。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song imperial intelligence chief, discreet court official in dark robes, sharp observant eyes, holding a folded blank secret letter, dim palace corridor background, restrained spy atmosphere, historical Chinese painting style, no readable text
```

### char_transport_judge

用途：转运判官、财税网络代表。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song transport finance official, formal robe, nervous composed expression, blank account books and grain warehouse shapes behind him, subtle sense of hidden corruption, refined historical portrait, no readable text
```

### char_palace_eunuch

用途：内廷和宦官军功集团。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song palace eunuch official, dark palace service robes, cautious and watchful expression, holding a blank command slip, warm dim imperial interior, historically grounded, no caricature, no readable text
```

### char_imperial_clan_elder

用途：宗室内廷代表。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of an elderly Northern Song imperial clan noble, dignified court robes, anxious protective expression, palace screen background, refined silk painting texture, restrained luxury, no readable text, no fantasy crown
```

### char_censor_official

用途：台谏代表。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song censor official, upright scholar in formal robes, intense moral gaze, holding a blank impeachment memorial, austere court background, refined ink and mineral pigment style, no readable text
```

### char_taixue_student

用途：太学生代表。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a young Northern Song Imperial Academy student activist, plain scholar robe, passionate expression, holding a blank petition sheet, academy courtyard background, refined historical painting style, no readable text
```

### char_grain_merchant

用途：粮商代表。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a wealthy Northern Song grain merchant, refined merchant robe, careful calculating expression, grain sacks and river boats subtly behind him, warm market lighting, historical Chinese portrait, no readable text
```

### char_palace_guard_commander

用途：殿前司将领。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song imperial guard commander, military robe and practical lamellar armor, guarded expression, palace gate background, historically grounded Song dynasty equipment, no fantasy armor, no readable text
```

### char_western_army_general

用途：西军将领。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song western army general from the frontier, rugged face, practical armor under cloak, wind and mountains suggested behind him, disciplined and wary expression, refined historical realism, no readable text
```

### char_hedong_defender

用途：河东守臣。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song Hedong frontier defender, scholar-general in worn official robe and armor, cold mountain fortress background, exhausted but steadfast expression, ink and mineral pigment historical portrait, no readable text
```

### char_hebei_scout_officer

用途：河北边报人物。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song scout officer from Hebei, travel-stained military clothing, carrying a blank dispatch tube, urgent expression, winter river crossing background, historical Chinese painting style, no text
```

### char_jin_envoy

用途：金使谈判。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Jin dynasty envoy during negotiations with the Northern Song, dignified northern steppe diplomatic attire, stern expression, fur-trimmed robe historically grounded, neutral palace background, no fantasy, no readable text
```

### char_jin_commander

用途：金军统帅。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Jin dynasty military commander in early 12th century northern armor, stern strategic gaze, winter campaign camp background, historically grounded equipment, muted iron and leather tones, no fantasy, no readable text
```

### char_palace_attendant

用途：内廷消息、宫中恐慌。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song palace attendant carrying blank folded documents, subdued robe, worried expression, dim palace corridor background, refined historical painting, no readable text
```

### char_warehouse_clerk

用途：账册证人。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a low-ranking Northern Song warehouse clerk, plain official robe, anxious expression, blank ledgers and grain warehouse background, subtle dramatic light, historical Chinese portrait, no readable text
```

### char_military_engineer

用途：工部城防工程。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song military engineer from the Ministry of Works, practical scholar robe, holding blank construction plans, city wall repair scene behind him, focused expression, refined historical painting, no text
```

### char_refugee_elder

用途：民心、京城士民。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of an elderly refugee from northern China during the Jingkang crisis, worn winter clothing, dignified sorrowful expression, distant city gate background, restrained historical realism in Chinese painting style, no gore, no readable text
```

### char_monastery_abbot

用途：寺观借款、民间资源。

建议尺寸：1024x1536。

Prompt:

```text
Portrait of a Northern Song monastery abbot involved in wartime relief and loans, simple robes, calm serious expression, temple courtyard and grain charity scene suggested behind him, refined historical Chinese portrait, no readable text
```

## 事件插图

### event_opening_jingkang_dream

用途：开场亡国梦。

建议尺寸：1920x1080。

Prompt:

```text
Dreamlike but restrained scene of the Jingkang disaster, Northern Song palace in cold dawn, imperial procession fading into northern mist, broken court banners, sorrowful historical atmosphere, Chinese handscroll painting style, no gore, no readable text, no fantasy effects
```

### event_jin_crossing_yellow_river

用途：金军逼近黄河急奏。

建议尺寸：1920x1080。

Prompt:

```text
Jin army crossing the Yellow River in winter during the Northern Song crisis, distant cavalry and banners, cold mist, river ice and muddy banks, cinematic Chinese historical painting, restrained colors, no gore, no readable text
```

### event_court_debate_war_peace

用途：战和朝议。

建议尺寸：1920x1080。

Prompt:

```text
Northern Song imperial court debate over war and peace, rows of scholar officials in formal robes facing the throne, tense atmosphere, warm palace interior, refined court painting style, no readable text, no modern elements
```

### event_li_gang_defends_gate

用途：李纲督守城门。

建议尺寸：1920x1080。

Prompt:

```text
Li Gang supervising the defense of a Bianjing city gate, Song soldiers preparing arrows and stones, civilians carrying supplies, tense but organized defense, historical Chinese painting style, muted cinnabar and ink, no gore, no readable text
```

### event_secret_archive_search

用途：皇城司夜查账册。

建议尺寸：1920x1080。

Prompt:

```text
Secret nighttime search of a Northern Song government archive, dark-robed imperial agents opening blank ledgers by lantern light, shelves of documents, tense quiet atmosphere, refined historical realism, no readable text
```

### event_palace_confrontation_ledger

用途：殿前对质账册案。

建议尺寸：1920x1080。

Prompt:

```text
Imperial court confrontation over a military payroll ledger, Northern Song officials kneeling before the throne, blank ledgers laid open, cinnabar seal paste on desk, tense dramatic court scene, no readable text, no gore
```

### event_granary_shortage

用途：粮仓不足、粮价上涨。

建议尺寸：1920x1080。

Prompt:

```text
Northern Song capital granary under wartime shortage, officials inspecting half-empty grain bins, worried workers, muted warm light, historical Chinese painting style, no readable text, no modern objects
```

### event_grain_market_panic

用途：京城粮价风波。

建议尺寸：1920x1080。

Prompt:

```text
Wartime grain market in Bianjing with anxious citizens, merchants guarding grain sacks, city guards watching, restrained tension, Song dynasty street architecture, handscroll-inspired composition, no readable signs, no violence
```

### event_taixue_petition

用途：太学生请愿。

建议尺寸：1920x1080。

Prompt:

```text
Northern Song Imperial Academy students gathering with blank petition papers outside a government gate, passionate but orderly crowd, scholar robes, winter light, refined Chinese historical painting, no readable text
```

### event_night_attack_city_gate

用途：金军夜攻城门。

建议尺寸：1920x1080。

Prompt:

```text
Night attack on a Bianjing city gate during a Northern Song siege, defenders on walls with torches, distant enemy silhouettes, flying arrows implied without gore, dramatic ink wash and cinnabar firelight, historically grounded, no readable text
```

### event_fire_oil_prepared

用途：火油、器械准备兑现。

建议尺寸：1920x1080。

Prompt:

```text
Song dynasty defenders preparing fire oil jars, stones and heavy crossbows on a city wall before a siege, disciplined workers and soldiers, warm torchlight, detailed historical equipment, no readable text, no fantasy
```

### event_qinwang_army_march

用途：勤王军行军。

建议尺寸：1920x1080。

Prompt:

```text
Northern Song relief army marching toward Bianjing along a winter road, banners, supply carts, disciplined soldiers, distant mountains, solemn historical atmosphere, Chinese handscroll painting style, no readable text
```

### event_hedong_fortress_appeal

用途：河东求援。

建议尺寸：1920x1080。

Prompt:

```text
Hedong frontier fortress under pressure in winter, Song defenders on walls, messenger departing with urgent dispatch, cold mountains, restrained historical Chinese painting, no readable text, no gore
```

### event_jin_envoy_demands

用途：金使索地索金。

建议尺寸：1920x1080。

Prompt:

```text
Jin envoy presenting harsh demands in a Northern Song palace hall, tense diplomatic scene, Song officials divided, envoy stern, blank document held forward, refined historical court painting, no readable text
```

### event_inner_court_panic

用途：宗室内廷南迁压力。

建议尺寸：1920x1080。

Prompt:

```text
Northern Song inner palace in wartime panic, imperial clan elders and attendants gathered around blank dispatches, anxious expressions, dim warm palace interior, refined historical painting, no readable text
```

### event_open_granary_relief

用途：开仓平粜。

建议尺寸：1920x1080。

Prompt:

```text
Northern Song officials opening a capital granary for controlled grain relief, citizens lined up, guards maintaining order, warm hopeful atmosphere, handscroll-style composition, no readable text
```

### event_decree_sealed

用途：颁诏过场。

建议尺寸：1920x1080。

Prompt:

```text
Close-up of a Northern Song imperial edict being sealed with cinnabar paste, emperor's hand and brush implied, blank silk scroll, inkstone and seal on wooden desk, dramatic warm light, no readable text
```

### event_faction_backlash

用途：派系串联反扑。

建议尺寸：1920x1080。

Prompt:

```text
Secret meeting of Northern Song officials in a dim private hall, blank memorial papers on table, anxious conspiratorial atmosphere, formal robes, lantern light, historical Chinese painting style, no readable text
```

### event_city_fire_risk

用途：城中火患。

建议尺寸：1920x1080。

Prompt:

```text
Controlled but dangerous fire near a Bianjing warehouse at night, Song soldiers and workers carrying water buckets, smoke rising, tense city defense atmosphere, no gore, no readable text, historical Chinese painting style
```

### event_victory_on_wall

用途：守城小胜。

建议尺寸：1920x1080。

Prompt:

```text
Aftermath of a successful defense on Bianjing city wall at dawn, exhausted Song defenders standing firm, enemy camp distant in mist, restrained hopeful mood, refined Chinese historical painting, no gore, no readable text
```

## 结局与章节图

### ending_bianjing_saved

用途：汴京保卫成功结局。

建议尺寸：1920x1080。

Prompt:

```text
Bianjing city at dawn after surviving a siege, city walls intact, banners calm, citizens and soldiers looking toward sunrise, restrained triumphant Northern Song historical painting, warm gold and ink tones, no readable text
```

### ending_humiliating_peace

用途：屈辱和议结局。

建议尺寸：1920x1080。

Prompt:

```text
Somber Northern Song court after signing a humiliating peace, officials silent, blank treaty on table, cold palace light, emperor isolated, refined historical painting, no readable text
```

### ending_southward_retreat

用途：南迁续命结局。

建议尺寸：1920x1080。

Prompt:

```text
Northern Song imperial convoy leaving Bianjing under gray sky, carts, officials and guards moving south, sorrowful restrained atmosphere, Chinese handscroll painting style, no readable text, no modern elements
```

### ending_city_falls

用途：汴京城破失败结局。

建议尺寸：1920x1080。

Prompt:

```text
Tragic fall of Bianjing shown with restraint, broken city gate in winter dawn, abandoned banners, smoke in distance, no gore, solemn historical Chinese painting style, no readable text
```

### ending_hedong_holds

用途：河东屏障成功。

建议尺寸：1920x1080。

Prompt:

```text
Hedong mountain fortress holding firm against northern pressure, Song banners on cold walls, enemy camp distant and stalled, austere heroic mood, refined Chinese historical painting, no readable text
```

### ending_reform_begins

用途：中兴开局结局。

建议尺寸：1920x1080。

Prompt:

```text
Northern Song court beginning wartime reforms after surviving crisis, officials presenting blank ledgers and military plans, emperor seated resolute, bright restrained palace light, refined court painting style, no readable text
```

### chapter_war_council

用途：章节过场，战局。

建议尺寸：1920x1080。

Prompt:

```text
Northern Song war council around a blank military map, generals and scholar officials debating, brushes, seals and dispatches on table, tense strategic atmosphere, historical Chinese painting style, no readable text
```

### chapter_people_of_bianjing

用途：章节过场，民心。

建议尺寸：1920x1080。

Prompt:

```text
People of Bianjing during wartime, scholars, merchants, soldiers and families in a Song dynasty street near a city gate, anxious but dignified, handscroll-inspired composition, no readable text
```

## 小图标素材

图标建议后处理为透明背景，并用前端叠加颜色状态。

### icon_treasury

用途：国库。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of an ancient Chinese treasury chest with strings of coins, Northern Song strategy game style, ink linework, muted gold and parchment, no text, transparent-style background
```

### icon_inner_treasury

用途：内帑。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of an imperial private treasury box with subtle cinnabar seal, Northern Song style, refined ink lines, muted gold, no text, transparent-style background
```

### icon_grain

用途：京城粮。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of grain sacks and a wooden measure, Song dynasty historical strategy style, warm parchment and wheat tones, no text, transparent-style background
```

### icon_morale

用途：战意/军心。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a Song dynasty battle banner and upright spear, restrained ink and cinnabar, historical strategy game icon, no text, transparent-style background
```

### icon_imperial_authority

用途：君威。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a blank imperial seal and brush, cinnabar and black ink, Northern Song court style, no readable characters, transparent-style background
```

### icon_public_support

用途：民心。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of gathered Song dynasty citizens represented by simple silhouettes and a protective city gate, warm ink style, no text, transparent-style background
```

### icon_jin_pressure

用途：金军威压。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a northern army banner beyond a river, dark cinnabar and ink, historical strategy game style, no readable text, transparent-style background
```

### icon_qinwang

用途：勤王响应。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a relief army banner moving along a road toward a city gate, Song dynasty strategy style, teal and ink accents, no text, transparent-style background
```

### icon_peace_pressure

用途：主和压力。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a blank treaty scroll under a heavy seal, tense diplomatic motif, muted parchment and cinnabar, no readable text, transparent-style background
```

### icon_secret_order

用途：密令。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a folded secret letter partly hidden under an ink brush, Northern Song intelligence motif, black ink and cinnabar, no text, transparent-style background
```

### icon_evidence

用途：证据。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a blank ledger page with a cinnabar verification mark, historical Chinese archive style, no readable text, transparent-style background
```

### icon_confrontation

用途：殿前对质。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of two blank memorial tablets facing an imperial seal, court confrontation motif, Northern Song strategy game style, no readable text, transparent-style background
```

### icon_decree

用途：拟旨/圣旨。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a blank imperial edict scroll with brush and seal, refined Song dynasty court style, no readable text, transparent-style background
```

### icon_city_gate_risk

用途：城门风险。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of an ancient Chinese city gate with a subtle crack mark, ink and muted cinnabar, historical strategy game style, no text, transparent-style background
```

### icon_fire_risk

用途：火患。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a controlled flame beside a granary silhouette, muted cinnabar and ink, Northern Song strategy game style, no readable text, transparent-style background
```

### icon_faction

用途：派系。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of interlinked blank seals on parchment, political faction network motif, Northern Song court style, no readable text, transparent-style background
```

### icon_report

用途：月末报告。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a blank monthly court report sheet with brush and seal paste, Song dynasty parchment style, no readable text, transparent-style background
```

### icon_history

用途：史册。

建议尺寸：256x256。

Prompt:

```text
Small UI icon of a bound ancient Chinese history book with blank cover, ink linework, warm parchment and dark thread binding, no readable text, transparent-style background
```

## 生成优先级

### 第一批必须生成

1. `map_north_china_strategy`
2. `map_bianjing_city_defense`
3. `bg_imperial_desk`
4. `ui_parchment_base`
5. `ui_memorial_sheet`
6. `ui_edict_scroll`
7. `ui_cinnabar_seal_blank`
8. `char_song_qinzong`
9. `char_li_gang`
10. `char_peace_chancellor`
11. `char_finance_minister`
12. `char_imperial_city司_chief`
13. `event_opening_jingkang_dream`
14. `event_palace_confrontation_ledger`
15. `event_night_attack_city_gate`
16. `ending_bianjing_saved`
17. `ending_city_falls`

### 第二批建议生成

- 剩余主要人物。
- 粮运、勤王、围城地图。
- 奏疏、账册、证据 UI 组件。
- 常用图标。
- 月末报告和章节图。

### 第三批扩展

- 更多事件插图。
- 派系专属背景。
- 多结局图。
- 不同季节的汴京和战线图。

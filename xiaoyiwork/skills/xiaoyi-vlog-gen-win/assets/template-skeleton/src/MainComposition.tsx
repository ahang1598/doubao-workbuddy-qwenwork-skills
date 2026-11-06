import React from 'react';
import {
	AbsoluteFill,
	Img,
	useCurrentFrame,
	useVideoConfig,
	interpolate,
	CalculateMetadataFunction,
	staticFile,
	Easing,
	spring,
} from 'remotion';
import {Audio} from '@remotion/media';
import {TransitionSeries, linearTiming, springTiming} from '@remotion/transitions';
import type {TransitionPresentation, TransitionPresentationComponentProps, TransitionTiming} from '@remotion/transitions';
import {wipe} from '@remotion/transitions/wipe';
import {clockWipe} from '@remotion/transitions/clock-wipe';
import {iris} from '@remotion/transitions/iris';
import {flip} from '@remotion/transitions/flip';
import {CameraMotionBlur} from '@remotion/motion-blur';
import {evolvePath} from '@remotion/paths';
import {Circle, Star, Heart, Polygon} from '@remotion/shapes';
import {z} from 'zod';
import {zColor} from '@remotion/zod-types';

// ─── Transition Style 白名单校验（附录A-1 双保险组件层）───
// slideEnterStyle/slideExitStyle 仅允许 scale/translate；rotate/skew/matrix 一律剥离并告警。
// 原因：旋转会让地平线/建筑/人像中轴线歪掉，观感像"拍歪了"而非艺术处理；
// prepare-project.sh 已在渲染前 grep 拦截，这里是最后防线。
const sanitizeStyle = (style?: Record<string, any>): Record<string, any> | undefined => {
	if (!style || typeof style.transform !== 'string') return style;
	const clean = style.transform
		.replace(/rotate[XYZ]?\([^)]*\)/g, '')
		.replace(/skew[XY]?\([^)]*\)/g, '')
		.replace(/matrix(3d)?\([^)]*\)/g, '')
		.trim();
	if (clean === style.transform) return style;
	console.warn(`[vlog] transition style 含 rotate/skew/matrix，已剥离（仅允许 scale/translate）: "${style.transform}" → "${clean}"`);
	return {...style, transform: clean || undefined};
};

// ─── P2-1：转场 timing 按类型分配 ───
// 位移/缩放型转场（slide-*/flip/zoom）用 springTiming：带轻微过冲回弹，比线性更生动；
// 透明度型转场（fade/dissolve/blur 等）保持 linearTiming（透明度交叉不适合过冲）。
// ⚠️ calculateMetadata 与渲染处必须共用本函数：springTiming.getDurationInFrames
// 含回弹余量，与 linear 帧数不同，两处不一致会导致总帧数算错、音画错位
const SPRING_TRANSITIONS: ReadonlyArray<string> = ['slide-left', 'slide-right', 'slide-up', 'slide-down', 'flip', 'zoom'];
const getTimingForTransition = (transition: string | undefined, durationInFrames: number): TransitionTiming => {
	if (transition && SPRING_TRANSITIONS.includes(transition)) {
		// damping 20 / stiffness 160 / mass 1：阻尼比 ≈0.79，过冲幅度 ≈1.7%——
		// 可感知的生动回弹但不夸张（slide 过冲 ≈22px@1280，zoom 过冲 scale ≈1.005）
		return springTiming({config: {damping: 20, stiffness: 160, mass: 1}, durationInFrames});
	}
	return linearTiming({durationInFrames});
};

// sqrt equal-power 曲线的输入防护：springTiming 过冲时 presentationProgress 可 >1，
// sqrt(1-p) 会产生 NaN 导致 opacity 失效（画面消失）。所有 sqrt 调用必须经此钳制
const clamp01 = (v: number): number => Math.min(1, Math.max(0, v));

// ─── Custom Transition: Equal-Power Fade（P1-2 替代官方线性 fade）───
// 官方 fade / 旧 dissolve / 旧 blur 透明度均为线性互补（p vs 1-p），
// 线性交叉中点 = 0.5A + 0.5B，亮暗差异大的两张图交叉时对比度塌陷发灰（dip-to-gray）。
// equal-power（sqrt 能量守恒）曲线是影视工业标准：中点亮度能量守恒，不再发灰。
const EqualPowerFadePresentation: React.FC<TransitionPresentationComponentProps<{
	shouldFadeOutExitingScene?: boolean;
}>> = ({children, presentationDirection, presentationProgress, passedProps}) => {
	const isEntering = presentationDirection === 'entering';
	const fadeExiting = passedProps.shouldFadeOutExitingScene ?? true;
	const opacity = isEntering
		? Math.sqrt(clamp01(presentationProgress))
		: fadeExiting
			? Math.sqrt(clamp01(1 - presentationProgress))
			: 1;
	return (
		<AbsoluteFill style={{opacity}}>
			{children}
		</AbsoluteFill>
	);
};
const fade = (props?: {shouldFadeOutExitingScene?: boolean}): TransitionPresentation<{shouldFadeOutExitingScene?: boolean}> => ({
	component: EqualPowerFadePresentation,
	props: props || {},
});

// 解析 style 中的 scale/translate 分量（其他分量视为违禁被忽略并告警）
const parseStyleTransform = (style?: Record<string, any>): {scale: number; tx: number; ty: number} | null => {
	if (!style || typeof style.transform !== 'string') return null;
	const t = style.transform;
	if (/rotate|skew|matrix/i.test(t)) {
		console.warn(`[vlog] slide enter/exitStyle 含 rotate/skew/matrix，已忽略（仅允许 scale/translate）: "${t}"`);
	}
	const scaleMatch = t.match(/scale\(\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)/);
	const txMatch = t.match(/translate\(\s*(-?[\d.]+)px(?:\s*,\s*(-?[\d.]+)px)?\s*\)/);
	return {
		scale: scaleMatch ? parseFloat(scaleMatch[1]) : 1,
		tx: txMatch ? parseFloat(txMatch[1]) : 0,
		ty: txMatch && txMatch[2] ? parseFloat(txMatch[2]) : 0,
	};
};

// ─── Custom Transition: Enhanced Slide（附录A-3 修复官方 slide 两大缺陷）───
// 官方 slide 将 enterStyle/exitStyle 静态展开且覆盖 directionStyle 的位移 transform，
// 导致：① "缩放增强滑入"变成全程静止悬挂 + 末尾跳变；② 滑动位移被吃掉退化为近似直切。
// 本实现：位移与 scale/translate 做 transform 合成（不覆盖），且自定义分量随 progress
// 渐进插值（entering: 样式值→identity；exiting: identity→样式值），
// SKILL.md 承诺的 "scale(0.9)→1 渐进缩放滑入" 真正成立。
type SlideDirection = 'from-left' | 'from-right' | 'from-top' | 'from-bottom';
const EnhancedSlidePresentation: React.FC<TransitionPresentationComponentProps<{
	direction?: SlideDirection;
	enterStyle?: Record<string, any>;
	exitStyle?: Record<string, any>;
}>> = ({children, presentationDirection, presentationProgress, passedProps}) => {
	const direction = passedProps.direction || 'from-left';
	const p = presentationProgress;
	// 与官方 slide 一致的 epsilon 接缝修正：转场接近结束时两场景轻微重叠，避免接缝白线
	const pEps = p === 1 ? p * 100 : p * 100 - 0.01;
	let translate = '';
	if (presentationDirection === 'exiting') {
		switch (direction) {
			case 'from-left': translate = `translateX(${pEps}%)`; break;
			case 'from-right': translate = `translateX(${-p * 100}%)`; break;
			case 'from-top': translate = `translateY(${pEps}%)`; break;
			case 'from-bottom': translate = `translateY(${-p * 100}%)`; break;
		}
	} else {
		switch (direction) {
			case 'from-left': translate = `translateX(${-100 + p * 100}%)`; break;
			case 'from-right': translate = `translateX(${100 - pEps}%)`; break;
			case 'from-top': translate = `translateY(${-100 + p * 100}%)`; break;
			case 'from-bottom': translate = `translateY(${100 - p * 100}%)`; break;
		}
	}
	const custom = parseStyleTransform(presentationDirection === 'entering' ? passedProps.enterStyle : passedProps.exitStyle);
	let scale = 1, tx = 0, ty = 0;
	if (custom) {
		if (presentationDirection === 'entering') {
			scale = custom.scale + (1 - custom.scale) * p;
			tx = custom.tx * (1 - p);
			ty = custom.ty * (1 - p);
		} else {
			scale = 1 + (custom.scale - 1) * p;
			tx = custom.tx * p;
			ty = custom.ty * p;
		}
	}
	const extra = (scale !== 1 || tx !== 0 || ty !== 0) ? ` scale(${scale}) translate(${tx}px, ${ty}px)` : '';
	return (
		<AbsoluteFill style={{transform: `${translate}${extra}`}}>
			{children}
		</AbsoluteFill>
	);
};
const enhancedSlide = (props?: {direction?: SlideDirection; enterStyle?: Record<string, any>; exitStyle?: Record<string, any>}): TransitionPresentation<{direction?: SlideDirection; enterStyle?: Record<string, any>; exitStyle?: Record<string, any>}> => ({
	component: EnhancedSlidePresentation,
	props: props || {},
});

// ─── Custom Transition: Dissolve (with slight scale, different from plain fade) ───
// P1-2：透明度换 sqrt equal-power 曲线，中点不再发灰塌陷
const DissolvePresentation: React.FC<TransitionPresentationComponentProps<{}>> = ({
	children,
	presentationDirection,
	presentationProgress,
}) => {
	const isEntering = presentationDirection === 'entering';
	const opacity = isEntering ? Math.sqrt(clamp01(presentationProgress)) : Math.sqrt(clamp01(1 - presentationProgress));
	const scale = isEntering
		? interpolate(presentationProgress, [0, 1], [1.05, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
		: interpolate(presentationProgress, [0, 1], [1, 1.05], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill style={{opacity, transform: `scale(${scale})`}}>
			{children}
		</AbsoluteFill>
	);
};
const dissolve = (): TransitionPresentation<{}> => ({
	component: DissolvePresentation,
	props: {},
});

// ─── Custom Transition: Zoom ───
// P1-3：缩放区间从 0.3→1 / 1→2 收窄到 0.7→1 / 1→1.35。
// 旧区间退出侧放大一倍 = 像素直接翻倍插值（等效 360p），马赛克感明显；
// 新区间放大侧（1.35 ≈ 等效 533p）叠 0→8px 轻微 blur 掩盖插值痕迹。
// P1-2：透明度同步换 sqrt equal-power 曲线。
const ZoomPresentation: React.FC<TransitionPresentationComponentProps<{direction?: 'in' | 'out'}>> = ({
	children,
	presentationDirection,
	presentationProgress,
	passedProps,
}) => {
	const dir = passedProps.direction || 'in';
	const isEntering = presentationDirection === 'entering';
	const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
	let scale: number;
	let blurPx: number;
	if (dir === 'in') {
		scale = isEntering
			? interpolate(presentationProgress, [0, 1], [0.7, 1], clamp)
			: interpolate(presentationProgress, [0, 1], [1, 1.35], clamp);
		// dir=in 的像素拉伸发生在退出侧（放大到 1.35）
		blurPx = isEntering ? 0 : interpolate(presentationProgress, [0, 1], [0, 8], clamp);
	} else {
		scale = isEntering
			? interpolate(presentationProgress, [0, 1], [1.35, 1], clamp)
			: interpolate(presentationProgress, [0, 1], [1, 0.7], clamp);
		// dir=out 的像素拉伸发生在进入侧（从 1.35 回落）
		blurPx = isEntering ? interpolate(presentationProgress, [0, 1], [8, 0], clamp) : 0;
	}
	const opacity = isEntering ? Math.sqrt(clamp01(presentationProgress)) : Math.sqrt(clamp01(1 - presentationProgress));
	return (
		<AbsoluteFill style={{opacity, transform: `scale(${scale})`, filter: `blur(${blurPx}px)`}}>
			{children}
		</AbsoluteFill>
	);
};
const zoom = (props?: {direction?: 'in' | 'out'}): TransitionPresentation<{direction?: 'in' | 'out'}> => ({
	component: ZoomPresentation,
	props: props || {},
});

// ─── Custom Transition: Blur ───
// P1-2：旧透明度平台设计（0→0.6→1）中点两图各 ~65% 叠加会短暂泛白，
// 换 sqrt equal-power 曲线后中点能量守恒，blur 本身即是强遮罩，过渡更干净。
const BlurPresentation: React.FC<TransitionPresentationComponentProps<{blurAmount?: number}>> = ({
	children,
	presentationDirection,
	presentationProgress,
	passedProps,
}) => {
	const blurPx = passedProps.blurAmount || 30;
	const isEntering = presentationDirection === 'entering';
	const blur = isEntering
		? interpolate(presentationProgress, [0, 1], [blurPx, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
		: interpolate(presentationProgress, [0, 1], [0, blurPx], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const opacity = isEntering
		? Math.sqrt(clamp01(presentationProgress))
		: Math.sqrt(clamp01(1 - presentationProgress));
	return (
		<AbsoluteFill style={{opacity, filter: `blur(${blur}px)`}}>
			{children}
		</AbsoluteFill>
	);
};
const blur = (props?: {blurAmount?: number}): TransitionPresentation<{blurAmount?: number}> => ({
	component: BlurPresentation,
	props: props || {},
});

// ─── Custom Transition: Glitch ───
const GlitchPresentation: React.FC<TransitionPresentationComponentProps<{}>> = ({
	children,
	presentationDirection,
	presentationProgress,
}) => {
	const isEntering = presentationDirection === 'entering';
	const p = presentationProgress;
	const glitchPhase = Math.floor(p * 8) % 2;
	const offsetX = glitchPhase === 0 ? interpolate(p, [0, 1], [20, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : interpolate(p, [0, 1], [-15, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const offsetY = glitchPhase === 0 ? interpolate(p, [0, 1], [-5, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : interpolate(p, [0, 1], [8, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const opacity = isEntering
		? interpolate(p, [0, 0.4, 1], [0, 0.8, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})
		: interpolate(p, [0, 0.6, 1], [1, 0.8, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	return (
		<AbsoluteFill style={{
			opacity,
			transform: `translate(${offsetX}px, ${offsetY}px)`,
			filter: `saturate(${1 + glitchPhase * 0.5})`,
		}}>
			{children}
		</AbsoluteFill>
	);
};
const glitch = (): TransitionPresentation<{}> => ({
	component: GlitchPresentation,
	props: {},
});

// ─── Zod Schema (parameterized video) ───
export const DecorationItemSchema = z.object({
	shape: z.enum(['circle', 'star', 'heart', 'polygon', 'arrow', 'underline', 'quote', 'divider', 'frame-corner']),
	position: z.enum(['top-left', 'top-right', 'bottom-left', 'bottom-right', 'center']),
	color: zColor(),
	size: z.number(),
	opacity: z.number().optional(),
});

export const TransitionPropsSchema = z.object({
	wipeDirection: z.enum(['from-left', 'from-top-left', 'from-top', 'from-top-right', 'from-right', 'from-bottom-right', 'from-bottom', 'from-bottom-left']).optional(),
	flipDirection: z.enum(['from-left', 'from-right', 'from-top', 'from-bottom']).optional(),
	flipPerspective: z.number().optional(),
	shouldFadeOutExitingScene: z.boolean().optional(),
	slideEnterStyle: z.record(z.string(), z.any()).optional(),
	slideExitStyle: z.record(z.string(), z.any()).optional(),
	zoomDirection: z.enum(['in', 'out']).optional(),
	blurAmount: z.number().optional(),
});

export const SceneDataSchema = z.object({
	image: z.string(),
	animation: z.enum(['zoom-in', 'zoom-out', 'pan-left', 'pan-right', 'tilt-up', 'tilt-down', '3d-tilt-left', '3d-tilt-right', 'static']),
	transition: z.enum(['fade', 'dissolve', 'slide-left', 'slide-right', 'slide-up', 'slide-down', 'wipe', 'clock-wipe', 'iris', 'flip', 'zoom', 'blur', 'glitch', 'none']).optional(),
	transitionDuration: z.number().optional(),
	transitionProps: TransitionPropsSchema.optional(),
	narration: z.string().optional(),
	effect: z.enum(['motion-blur', 'none']).optional(),
	caption: z.string().optional(),
	decorations: z.array(DecorationItemSchema).optional(),

});

export const ThemeColorsSchema = z.object({
	bgColor: zColor().optional(),
	textColor: zColor().optional(),
	accentColor: zColor().optional(),
});

export const VideoPropsSchema = z.object({
	title: z.string(),
	subtitle: z.string(),
	endText: z.string(),
	scenes: z.array(SceneDataSchema),
	sceneDurations: z.array(z.number()).optional(),
	totalFrames: z.number().optional(),
	bgmSrc: z.string().optional(),
	titleStroke: z.boolean().optional(),
	theme: ThemeColorsSchema.optional(),
	resolution: z.enum(['landscape', 'portrait']).optional(),
	// 封面图/片尾图文件名（放在 images/ 下）。设置后首尾帧显示该图（文字已生成在图中），不设则回退纯文字卡片
	titleImage: z.string().optional(),
	endImage: z.string().optional(),
});

// ─── Types (inferred from Zod) ───
export type DecorationItem = z.infer<typeof DecorationItemSchema>;
export type TransitionProps = z.infer<typeof TransitionPropsSchema>;
export type SceneData = z.infer<typeof SceneDataSchema>;
export type ThemeColors = z.infer<typeof ThemeColorsSchema>;
export type VideoProps = z.infer<typeof VideoPropsSchema>;



const defaultTheme: ThemeColors = {
	bgColor: '#1a1a2e',
	textColor: '#e8d5b7',
	accentColor: '#a89070',
};


const FPS = 24;
// P1-5：标题/片尾 90→72 帧（3.75s→3s），首尾节奏更紧凑；
// 片尾最后 24 帧 fade-out 与 BGM 末尾 1s 淡出窗口对齐（见 EndCard）
const TITLE_FRAMES = 72;
const END_FRAMES = 72;
const BUFFER_FRAMES = 15;
const TRANSITION_FRAMES = 18;

export const calculateMetadata: CalculateMetadataFunction<VideoProps> = async ({props}) => {
	const scenes = props.scenes || [];
	if (scenes.length === 0) return {durationInFrames: 300, props};

	// P2-9：sceneDurations 长度不匹配时不再静默兜底——console.warn 暴露编排错误，
	// 否则全部按 135 帧处理会无声掩盖第4步编排输出与场景数不一致的问题
	let sceneDurations: number[];
	if (props.sceneDurations?.length === scenes.length) {
		sceneDurations = props.sceneDurations;
	} else {
		if (props.sceneDurations) {
			console.warn(`[vlog] sceneDurations 长度(${props.sceneDurations.length})与 scenes 长度(${scenes.length})不匹配，全部按 ${5 * FPS + BUFFER_FRAMES} 帧兜底——请检查编排输出`);
		}
		sceneDurations = scenes.map(() => 5 * FPS + BUFFER_FRAMES);
	}

	// Use timing.getDurationInFrames() per Remotion best practices
	// P2-1：转场帧数必须按实际 timing 类型取值（springTiming 含回弹余量，
	// 与 linear 帧数不同）——与渲染处共用 getTimingForTransition，保证总帧数准确
	const titleTransitionFrames = linearTiming({durationInFrames: TRANSITION_FRAMES}).getDurationInFrames({fps: FPS});
	const totalTransitionFrames = titleTransitionFrames + (scenes.length > 1
		? scenes.slice(0, -1).reduce((sum, s) => {
			if (s.transition === 'none') return sum;
			const dur = s.transitionDuration || TRANSITION_FRAMES;
			return sum + getTimingForTransition(s.transition, dur).getDurationInFrames({fps: FPS});
		}, 0)
		: 0);

	// Also account for the end fade transition
	const endTransitionFrames = linearTiming({durationInFrames: TRANSITION_FRAMES}).getDurationInFrames({fps: FPS});
	const totalFrames = TITLE_FRAMES + sceneDurations.reduce((a, b) => a + b, 0) - totalTransitionFrames - endTransitionFrames + END_FRAMES;
	// Resolution: landscape=1280x720, portrait=720x1280
	const isPortrait = props.resolution === 'portrait';

	return {
		durationInFrames: totalFrames,
		width: isPortrait ? 720 : 1280,
		height: isPortrait ? 1280 : 720,
		props: {...props, sceneDurations, totalFrames},
	};
};

const kenBurnsEasing = Easing.bezier(0.25, 0.1, 0.25, 1.0);

type KenBurnsTransform = {
	scale: number;
	translateX: number;
	translateY: number;
	perspective: string;
	rotateX: number;
	rotateY: number;
	transformOrigin: string;
	shadowOpacity: number;
	shadowGradient: string;
};

const getKenBurnsTransform = (animation: string, frame: number, durationInFrames: number): KenBurnsTransform => {
	// P2-3：缓动按动画类型差异化，运动"性格"不再趋同
	// zoom-in:  ease-out（先快后慢，停在细节上有"落定"感）
	// zoom-out: ease-in-out（揭示感）
	// pan/tilt: 线性匀速（匀速移动是航拍/滑轨的体感）
	// 其余（3d-tilt/static）: 保持平滑 bezier
	const easingFor = (a: string): ((t: number) => number) => {
		if (a === 'zoom-in') return Easing.out(Easing.cubic);
		if (a === 'zoom-out') return Easing.inOut(Easing.cubic);
		if (a.startsWith('pan-') || a.startsWith('tilt-')) return Easing.linear;
		return kenBurnsEasing;
	};
	const progress = interpolate(frame, [0, durationInFrames], [0, 1], {
		extrapolateLeft: 'clamp',
		extrapolateRight: 'clamp',
		easing: easingFor(animation),
	});
	const clamp = {extrapolateLeft: 'clamp' as const, extrapolateRight: 'clamp' as const};
	// pan/tilt scale 提到 1.3：平移 ±150px / ±100px 时单侧溢出需 ≥ 平移量才不露黑边
	// 1280×1.3=1664（单侧溢出 192 > 150），720×1.3=936（单侧溢出 108 > 100），安全
	// P1-6：zoom 与 pan 缩放解耦——1.3 是 pan 不露边的推导结果，zoom 继承后幅度偏大
	// （720p 下 1.3 倍收尾帧等效 ≈554p，人像脸部糊化）；zoom 降到行业 Ken Burns 典型区间 1.15
	const base: Omit<KenBurnsTransform, 'scale'> = {
		translateX: 0, translateY: 0, perspective: '', rotateX: 0, rotateY: 0,
		transformOrigin: 'center center', shadowOpacity: 0, shadowGradient: '',
	};
	switch (animation) {
		case 'zoom-in': return {...base, scale: interpolate(progress, [0, 1], [1, 1.15], clamp)};
		case 'zoom-out': return {...base, scale: interpolate(progress, [0, 1], [1.15, 1], clamp)};
		case 'pan-left': return {...base, scale: 1.3, translateX: interpolate(progress, [0, 1], [150, -150], clamp)};
		case 'pan-right': return {...base, scale: 1.3, translateX: interpolate(progress, [0, 1], [-150, 150], clamp)};
		case 'tilt-up': return {...base, scale: 1.3, translateY: interpolate(progress, [0, 1], [100, -100], clamp)};
		case 'tilt-down': return {...base, scale: 1.3, translateY: interpolate(progress, [0, 1], [-100, 100], clamp)};
		// 平面旋转（rotate-cw/ccw）已移除：持续旋转违背照片 vlog 的摄影语言，
		// 让地平线/建筑/人像中轴线歪掉，观感像"拍歪了"而非艺术处理。
		// 真 3D tilt：rotateY ±8°（弱化透视，避免建筑/地平线明显歪斜）+ perspective 700
		// + rotateX 1.5° 复合视角（"歪头看"比单轴自然）+ transform-origin 落在近边（像翻页）
		// + 侧边阴影层模拟背光，强化空间感；scale 1.25 给 3D 旋转预留溢出余量
		// 仅限无明确水平参考线的场景（科技/产品/抽象），风景/建筑/人像禁用
		case '3d-tilt-left': return {
			...base,
			scale: 1.25,
			translateX: interpolate(progress, [0, 1], [40, -40], clamp),
			perspective: 'perspective(700px)',
			rotateX: interpolate(progress, [0, 1], [0, 1.5], clamp),
			rotateY: interpolate(progress, [0, 1], [0, -8], clamp),
			transformOrigin: 'right center',
			shadowOpacity: interpolate(progress, [0, 1], [0, 0.3], clamp),
			shadowGradient: 'linear-gradient(to left, transparent 55%, rgba(0,0,0,0.45))',
		};
		case '3d-tilt-right': return {
			...base,
			scale: 1.25,
			translateX: interpolate(progress, [0, 1], [-40, 40], clamp),
			perspective: 'perspective(700px)',
			rotateX: interpolate(progress, [0, 1], [0, 1.5], clamp),
			rotateY: interpolate(progress, [0, 1], [0, 8], clamp),
			transformOrigin: 'left center',
			shadowOpacity: interpolate(progress, [0, 1], [0, 0.3], clamp),
			shadowGradient: 'linear-gradient(to right, transparent 55%, rgba(0,0,0,0.45))',
		};
		// static 改为单峰呼吸：振幅 1→1.04→1，周期覆盖整段，避免短周期抖动感
		case 'static': return {
			...base,
			scale: interpolate(progress, [0, 0.5, 1], [1, 1.04, 1], clamp),
			translateX: interpolate(progress, [0, 0.33, 0.67, 1], [0, 5, -5, 0], clamp),
			translateY: interpolate(progress, [0, 0.33, 0.67, 1], [0, -3, 3, 0], clamp),
		};
		default: return {...base, scale: 1};
	}
};

// Map transition name + props to Remotion presentation
// 返回类型显式注解为 TransitionPresentation<any>：各转场工厂的泛型 props 不同
// （ClockWipeProps/FlipProps/自定义等），联合类型无法直接赋给 TransitionSeries.Transition
const getTransitionPresentation = (transition: string | undefined, width: number = 1280, height: number = 720, tProps?: TransitionProps): TransitionPresentation<any> | null => {
	switch (transition || 'fade') {
		case 'fade': return fade({shouldFadeOutExitingScene: tProps?.shouldFadeOutExitingScene ?? true});
		case 'dissolve': return dissolve();
		case 'slide-left': return enhancedSlide({direction: 'from-right', enterStyle: tProps?.slideEnterStyle, exitStyle: tProps?.slideExitStyle});
		case 'slide-right': return enhancedSlide({direction: 'from-left', enterStyle: tProps?.slideEnterStyle, exitStyle: tProps?.slideExitStyle});
		case 'slide-up': return enhancedSlide({direction: 'from-bottom', enterStyle: tProps?.slideEnterStyle, exitStyle: tProps?.slideExitStyle});
		case 'slide-down': return enhancedSlide({direction: 'from-top', enterStyle: tProps?.slideEnterStyle, exitStyle: tProps?.slideExitStyle});
		case 'wipe': return wipe({direction: tProps?.wipeDirection || 'from-left', outerEnterStyle: sanitizeStyle(tProps?.slideEnterStyle), outerExitStyle: sanitizeStyle(tProps?.slideExitStyle), innerEnterStyle: sanitizeStyle(tProps?.slideEnterStyle), innerExitStyle: sanitizeStyle(tProps?.slideExitStyle)});
		case 'clock-wipe': return clockWipe({width, height, outerEnterStyle: sanitizeStyle(tProps?.slideEnterStyle), outerExitStyle: sanitizeStyle(tProps?.slideExitStyle), innerEnterStyle: sanitizeStyle(tProps?.slideEnterStyle), innerExitStyle: sanitizeStyle(tProps?.slideExitStyle)});
		case 'iris': return iris({width, height, outerEnterStyle: sanitizeStyle(tProps?.slideEnterStyle), outerExitStyle: sanitizeStyle(tProps?.slideExitStyle), innerEnterStyle: sanitizeStyle(tProps?.slideEnterStyle), innerExitStyle: sanitizeStyle(tProps?.slideExitStyle)});
		case 'flip': return flip({direction: tProps?.flipDirection || 'from-left', perspective: tProps?.flipPerspective || 1000, outerEnterStyle: sanitizeStyle(tProps?.slideEnterStyle), outerExitStyle: sanitizeStyle(tProps?.slideExitStyle), innerEnterStyle: sanitizeStyle(tProps?.slideEnterStyle), innerExitStyle: sanitizeStyle(tProps?.slideExitStyle)});
		case 'zoom': return zoom({direction: tProps?.zoomDirection || 'in'});
		case 'blur': return blur({blurAmount: tProps?.blurAmount || 30});
		case 'glitch': return glitch();
		case 'none': return null;
		default: return fade();
	}
};

// ─── Effect: Caption Overlay ───
const CaptionOverlay: React.FC<{text: string}> = ({text}) => {
	const frame = useCurrentFrame();
	const {durationInFrames, width, height} = useVideoConfig();
	// P2-3：opacity 淡入淡出 ease-out 化——人眼对低亮度段变化更敏感，
	// 线性淡入主观上"前急后缓"，ease-out 更接近感知均匀
	const opacity = interpolate(frame, [0, 15, durationInFrames - 15, durationInFrames], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)});
	// D5：排版按画幅比例化——水平方向（字号/水平 padding/字距）按宽度比 scaleW、
	// 垂直方向（底部安全区/垂直 padding）按高度比 scaleH。
	// 两个方向必须分开：竖屏 paddingBottom 若按宽度比缩到 34px 会贴底
	// （相对 1280 高仅 2.6%，远低于横屏 60/720=8.3% 的设计占比），
	// 按高度比 60×(1280/720)≈107px 才能保持垂直安全区等效。
	// 横屏 1280×720 时 scaleW=scaleH=1，与旧版行为完全一致（无回归风险）
	const scaleW = width / 1280;
	const scaleH = height / 720;
	return (
		<AbsoluteFill style={{justifyContent: 'flex-end', alignItems: 'center', paddingBottom: 60 * scaleH, opacity}}>
			<div style={{
				backgroundColor: 'rgba(0,0,0,0.6)',
				padding: `${8 * scaleH}px ${24 * scaleW}px`,
				borderRadius: 8 * scaleW,
				maxWidth: '80%',
			}}>
				<span style={{color: '#fff', fontSize: Math.round(28 * scaleW), fontFamily: '"Helvetica Neue", Helvetica, Arial, sans-serif', fontWeight: 600, textShadow: '0 2px 4px rgba(0,0,0,0.5)'}}>{text}</span>
			</div>
		</AbsoluteFill>
	);
};

// ─── Effect: Geometric Decorations ───
const positionToStyle = (pos: string, size: number, scaleW: number = 1, scaleH: number = 1): React.CSSProperties => {
	// D5：安全区边距双向比例化——left/right 按宽度比、top/bottom 按高度比
	// （bottom 额外 50px 为避开 caption 区域，与 caption paddingBottom 同按高度比）
	const marginX = 30 * scaleW;
	const marginY = 30 * scaleH;
	switch (pos) {
		case 'top-left': return {top: marginY, left: marginX};
		case 'top-right': return {top: marginY, right: marginX};
		case 'bottom-left': return {bottom: marginY + 50 * scaleH, left: marginX};
		case 'bottom-right': return {bottom: marginY + 50 * scaleH, right: marginX};
		case 'center': return {top: `calc(50% - ${size / 2}px)`, left: `calc(50% - ${size / 2}px)`};
		default: return {top: marginY, left: marginX};
	}
};

const ShapeRenderer: React.FC<{item: DecorationItem}> = ({item}) => {
	const frame = useCurrentFrame();
	const {fps, width, height} = useVideoConfig();
	const scale = spring({frame, fps, config: {damping: 12, stiffness: 80}});
	const opacity = item.opacity ?? 0.6;
	const posStyle = positionToStyle(item.position, item.size, width / 1280, height / 720);
	const svgStyle: React.CSSProperties = {opacity: opacity * scale, width: item.size, height: item.size};

	// P1-7：线条类装饰——与任何风格兼容的"高级"选项。
	// 不走实心几何形的 spring 弹入（贴纸感根源），改用描边生长 / 中心展开 / 淡入：
	// underline 标题下划线生长、divider 两端渐隐细分隔线、quote 引号淡入、frame-corner 取景框四角。
	// size 语义：underline/divider 线长=size×2；quote 字号=size；frame-corner 框边长=size×2
	if (item.shape === 'underline' || item.shape === 'divider' || item.shape === 'quote' || item.shape === 'frame-corner') {
		const grow = interpolate(frame, [0, 20], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});
		const lineLen = item.size * 2;
		// 定位容器必须用普通 div（尺寸由内容撑开，position 才精确生效）——
		// AbsoluteFill 全屏拉伸 + flex 对齐会让 posStyle 失效、装饰全部堆在左上角（存量 bug）。
		// center 用 translate(-50%,-50%) 精确居中（线条类宽高与 size 不成 1:1，calc 偏移会偏）
		const linePos: React.CSSProperties = item.position === 'center'
			? {top: '50%', left: '50%', transform: 'translate(-50%, -50%)'}
			: posStyle;
		return (
			<div style={{position: 'absolute', ...linePos}}>
				{item.shape === 'underline' && (
					<svg width={lineLen} height={6} style={{opacity}}>
						<line x1={0} y1={3} x2={lineLen} y2={3} stroke={item.color} strokeWidth={2} strokeLinecap="round"
							strokeDasharray={lineLen} strokeDashoffset={(1 - grow) * lineLen} />
					</svg>
				)}
				{item.shape === 'divider' && (
					<div style={{
						width: lineLen, height: 1.5, opacity: opacity * grow,
						background: `linear-gradient(to right, transparent, ${item.color}, transparent)`,
						transform: `scaleX(${grow})`, transformOrigin: 'center center',
					}} />
				)}
				{item.shape === 'quote' && (
					// 西文弯引号“在 Georgia/Times 中必有字形，不依赖中文字体
					<div style={{
						fontSize: item.size, color: item.color, opacity: opacity * grow,
						fontFamily: '"Georgia", "Times New Roman", serif', lineHeight: 1,
						transform: `translateY(${(1 - grow) * 8}px)`,
					}}>“</div>
				)}
				{item.shape === 'frame-corner' && (() => {
					const box = item.size * 2;
					const arm = Math.max(12, item.size * 0.3);
					const l = arm * 2; // 单条 L path 总长（横臂+竖臂）
					const corner = (d: string, key: string) => (
						<path key={key} d={d} stroke={item.color} strokeWidth={2} fill="none" strokeLinecap="round"
							strokeDasharray={l} strokeDashoffset={(1 - grow) * l} />
					);
					return (
						<svg width={box} height={box} style={{opacity}} viewBox={`0 0 ${box} ${box}`}>
							{corner(`M ${arm} 0 L 0 0 L 0 ${arm}`, 'tl')}
							{corner(`M ${box - arm} 0 L ${box} 0 L ${box} ${arm}`, 'tr')}
							{corner(`M ${box} ${box - arm} L ${box} ${box} L ${box - arm} ${box}`, 'br')}
							{corner(`M ${arm} ${box} L 0 ${box} L 0 ${box - arm}`, 'bl')}
						</svg>
					);
				})()}
			</div>
		);
	}

	// ⚠️ 定位容器从 AbsoluteFill 改为 div：AbsoluteFill 全屏拉伸（left:0+right:0 同时存在）
	// + flex 对齐使 posStyle 的 top/right/bottom 失效，旧几何装饰实际全部堆在左上角
	// （star 指定 top-right 实测渲染在左上角，P1-7 差分验证发现的存量 bug）。
	// div 尺寸由内容撑开，position 精确生效
	return (
		<div style={{position: 'absolute', ...posStyle, transform: `scale(${scale})`}}>
			{item.shape === 'circle' && <Circle radius={item.size / 2} fill={item.color} style={svgStyle} />}
			{item.shape === 'star' && <Star points={5} innerRadius={item.size * 0.4} outerRadius={item.size / 2} fill={item.color} style={svgStyle} />}
			{item.shape === 'heart' && <Heart height={item.size} fill={item.color} style={svgStyle} />}
			{item.shape === 'polygon' && <Polygon points={6} radius={item.size / 2} cornerRadius={0} edgeRoundness={null} fill={item.color} style={svgStyle} />}
			{item.shape === 'arrow' && <svg width={item.size} height={item.size} viewBox="0 0 24 24" fill={item.color} style={svgStyle}><path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/></svg>}
		</div>
	);
};

// ─── Ken Burns Image (separate component so CameraMotionBlur can track frame changes) ───
const KenBurnsImage: React.FC<{image: string; animation: string; sceneDuration: number; transitionDuration?: number; transition?: string; theme?: ThemeColors}> = ({image, animation, sceneDuration, transitionDuration, transition, theme}) => {
	const frame = useCurrentFrame();
	const transDur = transitionDuration || TRANSITION_FRAMES;
	const hasTransition = transition && transition !== 'none';
	// 修复转场闪黑的正确做法：转场期间冻结退出场景的 Ken Burns 变换，
	// 让退出场景静止淡出，而不是一边运动一边淡出形成"鬼影"。
	// 不再用 opacity=0 瞬间砍掉退出场景——那会让 crossfade 退化成 dip-to-black，
	// 也会让 slide/wipe 等揭示类转场背后露出黑底。
	const effectiveFrame = (hasTransition && frame >= sceneDuration - transDur)
		? sceneDuration - transDur
		: frame;
	const kb = getKenBurnsTransform(animation, effectiveFrame, sceneDuration);

	const transformParts = [
		kb.perspective ? kb.perspective : '',
		`scale(${kb.scale})`,
		`translate(${kb.translateX}px, ${kb.translateY}px)`,
		kb.rotateX ? `rotateX(${kb.rotateX}deg)` : '',
		kb.rotateY ? `rotateY(${kb.rotateY}deg)` : '',
	].filter(Boolean).join(' ');

	const bgColor = theme?.bgColor || defaultTheme.bgColor!;

	return (
		<AbsoluteFill style={{backgroundColor: bgColor}}>
			{/* 模糊填充背景层：准备阶段已按输出尺寸完成 cover、模糊和压暗，
			    渲染时只做变换，避免逐帧 CSS blur 创建高负载离屏表面；
			    主体层用 contain 不裁切图片内容，两层配合 = 不丢画面也无黑边 */}
			{/* P2-8：背景模糊层随主体同向弱联动（系数 0.3），消除"前景贴片"感——
			    旧版主体 pan/zoom 而背景完全静止（20260728_1945 帧 350-400 可见
			    pan 平移露出的模糊背景竖直接缝，即为实证）。
			    只取 scale/translate 分量：3D 旋转不传给模糊背景（无意义且易露边）。
			    不露边论证（最严苛场景 = 竖屏 pan）：
			    720×1.25=900，单侧溢出 90px > 位移 150×0.3=45px，安全。 */}
			<AbsoluteFill>
				<Img src={staticFile(`images/__blur/${image}.blur.jpg`)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${1.25 + (kb.scale - 1) * 0.3}) translate(${kb.translateX * 0.3}px, ${kb.translateY * 0.3}px)`}} />
			</AbsoluteFill>
			{/* 主体层：Ken Burns 变换 + 3D 侧边阴影（阴影随主体一起旋转，模拟背光） */}
			<AbsoluteFill style={{transform: transformParts, transformOrigin: kb.transformOrigin}}>
				<Img src={staticFile(`images/${image}`)} style={{width: '100%', height: '100%', objectFit: 'contain'}} />
				{kb.shadowOpacity > 0 && (
					<AbsoluteFill style={{background: kb.shadowGradient, opacity: kb.shadowOpacity, pointerEvents: 'none'}} />
				)}
			</AbsoluteFill>
		</AbsoluteFill>
	);
};

// ─── SVG Stroke Grow (描边生长装饰) ───
const StrokeGrow: React.FC<{path: string; color: string; strokeWidth?: number; duration?: number; position?: React.CSSProperties; viewBox?: string}> = ({path, color, strokeWidth = 2, duration = 60, position, viewBox}) => {
	const frame = useCurrentFrame();
	const progress = interpolate(frame, [0, duration], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
	const {strokeDasharray, strokeDashoffset} = evolvePath(progress, path);

	return (
		<svg style={{position: 'absolute', ...position, pointerEvents: 'none', overflow: 'visible'}} viewBox={viewBox || '0 0 1280 720'}>
			<path
				d={path}
				stroke={color}
				strokeWidth={strokeWidth}
				fill="none"
				strokeDasharray={strokeDasharray}
				strokeDashoffset={strokeDashoffset}
				strokeLinecap="round"
				opacity={0.4}
			/>
		</svg>
	);
};

// ─── Vignette Overlay ───
const VignetteOverlay: React.FC<{strength?: number}> = ({strength = 0.2}) => {
	return (
		<AbsoluteFill style={{
			background: `radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,${strength}) 100%)`,
			pointerEvents: 'none',
		}} />
	);
};

// 主题色 hex → rgba 动态派生（P0-3 修复：colorMap 未收录的主题如纯白/莫兰迪，
// 原回退到暗金紫色叠加导致画面偏紫，现按 bgColor 自身派生同色 overlay）
const hexToRgba = (hex: string, alpha: number): string => {
	const n = parseInt(hex.replace('#', ''), 16);
	if (isNaN(n) || hex.replace('#', '').length < 6) return `rgba(0, 0, 0, ${alpha})`;
	return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
};

// ─── Color Grade Overlay ───
const ColorGradeOverlay: React.FC<{theme?: ThemeColors}> = ({theme}) => {
	// 根据主题色调加轻微色彩叠加，统一画面色调
	const colorMap: Record<string, string> = {
		'#1a1a2e': 'rgba(20, 10, 40, 0.08)',
		'#2d1b0e': 'rgba(60, 30, 0, 0.1)',
		'#0a1628': 'rgba(0, 20, 60, 0.1)',
		'#0d2818': 'rgba(0, 40, 20, 0.08)',
		'#2d0a1e': 'rgba(50, 0, 30, 0.08)',
		'#0a0a0a': 'rgba(0, 30, 15, 0.06)',
	};
	const bgColor = theme?.bgColor || '#1a1a2e';
	const grade = colorMap[bgColor] || hexToRgba(bgColor, 0.08);
	return (
		<AbsoluteFill style={{
			background: grade,
			pointerEvents: 'none',
			mixBlendMode: 'overlay',
		}} />
	);
};

// ─── Scene Component ───
const Scene: React.FC<{scene: SceneData; sceneDuration: number; theme?: ThemeColors}> = ({scene, sceneDuration, theme}) => {
	const imageElement = <KenBurnsImage image={scene.image} animation={scene.animation} sceneDuration={sceneDuration} transitionDuration={scene.transitionDuration} transition={scene.transition} theme={theme} />;

	// 快速运动动画或显式 motion-blur 效果时启用 CameraMotionBlur
	const needsMotionBlur = scene.effect === 'motion-blur';

	const wrappedImage = needsMotionBlur ? (
		<CameraMotionBlur shutterAngle={180} samples={4}>
			{imageElement}
		</CameraMotionBlur>
	) : imageElement;

	return (
		<AbsoluteFill style={{backgroundColor: theme?.bgColor || defaultTheme.bgColor!}}>
			{wrappedImage}
			{/* P1-1：Vignette/ColorGrade 改为全片统一启用。
				旧设计按 caption/decorations 条件启用，导致有字幕场景有暗角、无字幕场景没有，
				观众感知到画面"一会儿压暗一会儿亮"、色调跳变——vlog 质感第一原则是全片统一。
				暗角强度降到 0.1（轻量统一质感，不形成"黑框"感）。 */}
			<VignetteOverlay strength={0.1} />
			<ColorGradeOverlay theme={theme} />
			{scene.caption && <AbsoluteFill style={{
				background: 'linear-gradient(to top, rgba(0,0,0,0.5) 0%, transparent 30%)',
				bottom: 0,
				height: '25%',
				top: undefined,
			}} />}
				{scene.caption && <CaptionOverlay text={scene.caption} />}
			{scene.decorations?.map((dec, i) => <ShapeRenderer key={`dec-${i}`} item={dec} />)}
		</AbsoluteFill>
	);
};

// ─── Title Card with optional SVG stroke ───
const TitleCard: React.FC<{title: string; subtitle: string; titleStroke?: boolean; titleImage?: string; theme: ThemeColors; videoWidth?: number; videoHeight?: number}> = ({title, subtitle, titleStroke, titleImage, theme, videoWidth, videoHeight}) => {
	const bgColor = theme.bgColor || defaultTheme.bgColor!;
	const textColor = theme.textColor || defaultTheme.textColor!;
	const accentColor = theme.accentColor || defaultTheme.accentColor!;
	// D5：标题/副标题字号与字距按 videoWidth 比例化（基准 1280，竖屏 ×0.5625）
	const uiScale = (videoWidth || 1280) / 1280;
	// 垂直间距（副标题 marginTop）按高度比，与 CaptionOverlay 的 scaleH 同理
	const vScale = (videoHeight || 720) / 720;

	const frame = useCurrentFrame();
	// P1-5：TITLE_FRAMES 90→72 后各动画区间同步收缩（fadeOut 最后 20 帧淡出不变，起点 70→52）
	// P2-3：淡入淡出统一 ease-out（感知均匀，见 CaptionOverlay 注释）
	const tOp = interpolate(frame, [0, 20], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)});
	const sOp = interpolate(frame, [15, 35], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)});
	const fadeOut = interpolate(frame, [TITLE_FRAMES - 20, TITLE_FRAMES], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)});
	const scale = interpolate(frame, [0, 30], [0.9, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});

	// 封面图分支：标题/副标题文字已生成在图中，这里只渲染图片 + 微妙 zoom-in Ken Burns + 淡入/淡出
	if (titleImage) {
		const kb = getKenBurnsTransform('zoom-in', frame, TITLE_FRAMES);
return (
				<AbsoluteFill style={{backgroundColor: bgColor, opacity: Math.min(tOp, fadeOut)}}>
				<AbsoluteFill style={{
					transform: `scale(${kb.scale}) translate(${kb.translateX}px, ${kb.translateY}px)`,
				}}>
					<Img src={staticFile(`images/${titleImage}`)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
				</AbsoluteFill>
			</AbsoluteFill>
		);
	}

	// SVG stroke dash animation（P1-5：TITLE_FRAMES 72 下描边 60 帧完成，留 12 帧实心展示+淡出）
	const strokeProgress = titleStroke ? interpolate(frame, [10, 60], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) : 1;

	return (
		<AbsoluteFill style={{backgroundColor: bgColor, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', opacity: Math.min(tOp, fadeOut)}}>
			<div style={{
				fontSize: Math.round(60 * uiScale),
				fontWeight: 'normal',
				color: titleStroke && strokeProgress < 1 ? 'transparent' : textColor,
				fontFamily: '"Georgia", "Times New Roman", serif',
				letterSpacing: 8 * uiScale,
				transform: `scale(${scale})`,
				WebkitTextStroke: titleStroke && strokeProgress < 1 ? `1px ${textColor}` : undefined,
				clipPath: titleStroke ? `inset(0 ${interpolate(strokeProgress, [0, 1], [100, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'})}% 0 0)` : undefined,
			}}>{title}</div>
			<div style={{fontSize: Math.round(24 * uiScale), color: accentColor, marginTop: 20 * vScale, opacity: sOp, fontFamily: '"Georgia", "Times New Roman", serif', letterSpacing: 4 * uiScale}}>{subtitle}</div>
			{/* P0-2 修复：弧线 path 按实际分辨率比例生成，竖屏(720×1280)不再错位到画布外 */}
			<StrokeGrow
				path={`M ${(videoWidth || 1280) * 0.42} ${(videoHeight || 720) * 0.58} Q ${(videoWidth || 1280) * 0.5} ${(videoHeight || 720) * 0.61} ${(videoWidth || 1280) * 0.58} ${(videoHeight || 720) * 0.58}`}
				color={accentColor}
				strokeWidth={1.5}
				duration={50}
				position={{top: 0, left: 0, width: '100%', height: '100%'}}
				viewBox={`0 0 ${videoWidth || 1280} ${videoHeight || 720}`}
			/>
		</AbsoluteFill>
	);
};

const EndCard: React.FC<{text: string; endImage?: string; theme: ThemeColors}> = ({text, endImage, theme}) => {
	const bgColor = theme.bgColor || defaultTheme.bgColor!;
	const textColor = theme.textColor || defaultTheme.textColor!;
	const frame = useCurrentFrame();
	// D5：片尾字号/字距按 videoWidth 比例化（基准 1280）
	const {width: endCardWidth} = useVideoConfig();
	const uiScale = endCardWidth / 1280;
	// P1-5：片尾新增最后 24 帧（1s）fade-to-bg 淡出，与 BGM 末尾 1s 淡出窗口对齐——
	// 修复旧版"声音在消失、画面却突然被播放器截断"的声画收尾不同步问题。
	// EndCard 是最后一个 Sequence，其末尾帧即全片末尾帧；淡到底色 = 显示 bgColor 底，无黑帧。
	const fadeIn = interpolate(frame, [0, 30], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)});
	const fadeOut = interpolate(frame, [END_FRAMES - 24, END_FRAMES], [1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.quad)});
	const opacity = Math.min(fadeIn, fadeOut);
	const scale = interpolate(frame, [0, 30], [0.9, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp', easing: Easing.out(Easing.cubic)});

	// 片尾图分支：片尾文字已生成在图中，这里只渲染图片 + 淡入/缩放
	if (endImage) {
return (
				<AbsoluteFill style={{backgroundColor: bgColor, opacity}}>
				<AbsoluteFill style={{transform: `scale(${scale})`}}>
					<Img src={staticFile(`images/${endImage}`)} style={{width: '100%', height: '100%', objectFit: 'cover'}} />
				</AbsoluteFill>
			</AbsoluteFill>
		);
	}

	return (
		<AbsoluteFill style={{backgroundColor: bgColor, display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', opacity}}>
			<div style={{fontSize: Math.round(36 * uiScale), color: textColor, fontFamily: '"Georgia", "Times New Roman", serif', letterSpacing: 4 * uiScale, transform: `scale(${scale})`}}>{text}</div>
		</AbsoluteFill>
	);
};

export const MainComposition: React.FC<VideoProps> = (rawProps) => {
	const {title, subtitle, endText, scenes, sceneDurations, bgmSrc, titleStroke, titleImage, endImage, theme: rawTheme, totalFrames: rawTotalFrames} = rawProps;
	const theme = {...defaultTheme, ...rawTheme};
	const {width: videoWidth, height: videoHeight} = useVideoConfig();

	if (!scenes || scenes.length === 0) {
		return <AbsoluteFill style={{backgroundColor: theme.bgColor || defaultTheme.bgColor!}} />;
	}

	const totalFrames = rawTotalFrames || 300;

	const children: React.ReactNode[] = [];

	children.push(
		<TransitionSeries.Sequence key="title" durationInFrames={TITLE_FRAMES} premountFor={FPS}>
			<TitleCard title={title} subtitle={subtitle} titleStroke={titleStroke} titleImage={titleImage} theme={theme} videoWidth={videoWidth} videoHeight={videoHeight} />
		</TransitionSeries.Sequence>
	);

	children.push(
		<TransitionSeries.Transition
			key="trans-title"
			presentation={fade()}
			timing={linearTiming({durationInFrames: TRANSITION_FRAMES})}
		/>
	);

	scenes.forEach((scene, i) => {
		const duration = sceneDurations?.[i] || 150;

		children.push(
			<TransitionSeries.Sequence key={`scene-${i}`} durationInFrames={duration} premountFor={FPS}>
				<Scene scene={scene} sceneDuration={duration} theme={theme} />
			</TransitionSeries.Sequence>
		);

		if (i < scenes.length - 1) {
			const presentation = getTransitionPresentation(scene.transition, videoWidth, videoHeight, scene.transitionProps);
			if (presentation) {
				children.push(
					<TransitionSeries.Transition
						key={`trans-${i}`}
						presentation={presentation}
						timing={getTimingForTransition(scene.transition, scene.transitionDuration || TRANSITION_FRAMES)}
					/>
				);
			}
		}
	});

	children.push(
		<TransitionSeries.Transition
			key="trans-end"
			presentation={fade()}
			timing={linearTiming({durationInFrames: TRANSITION_FRAMES})}
		/>
	);

	children.push(
		<TransitionSeries.Sequence key="end" durationInFrames={END_FRAMES} premountFor={FPS}>
			<EndCard text={endText} endImage={endImage} theme={theme} />
		</TransitionSeries.Sequence>
	);

	const bgmAudio = bgmSrc ? (
		<Audio
			src={staticFile(`audio/${bgmSrc}`)}
			loop
			loopVolumeCurveBehavior="extend"
			volume={(f) => {
				const fadeIn = interpolate(f, [0, FPS * 2], [0, 0.8], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
				const fadeOutStart = totalFrames - 1 * FPS;
				if (f >= fadeOutStart) {
					return interpolate(f, [fadeOutStart, totalFrames], [0.8, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
				}
				return fadeIn;
			}}
			trimAfter={totalFrames}
		/>
	) : null;

	return (
		<AbsoluteFill style={{backgroundColor: theme.bgColor || defaultTheme.bgColor!}}>
			<TransitionSeries>
				{children}
			</TransitionSeries>
			{bgmAudio}
		</AbsoluteFill>
	);
};

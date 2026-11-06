import {Composition} from 'remotion';
import {MainComposition, calculateMetadata, VideoPropsSchema} from './MainComposition';
import type {VideoProps} from './MainComposition';

const defaultProps = {
	title: '',
	subtitle: '',
	endText: '',
	scenes: [],
} satisfies VideoProps;

export const RemotionRoot = () => {
	return (
		<Composition
			id="MainComposition"
			component={MainComposition}
			defaultProps={defaultProps}
			durationInFrames={300}
			fps={24}
			width={1280}
			height={720}
			calculateMetadata={calculateMetadata}
			schema={VideoPropsSchema}
		/>
	);
};
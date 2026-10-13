import { css } from 'styled-components';
import { LEVEL_3, LEVEL_4 } from '@ali/we-design-3';

export const CSS_SCROLLER = css`
  overflow: auto;
  overflow: overlay;

  &::-webkit-scrollbar {
    width: 10px;
    height: 10px;
  }

  &::-webkit-scrollbar-button {
    display: none;
    height: 0;
    width: 0;
  }

  &::-webkit-scrollbar-corner {
    background-color: transparent;
  }

  &::-webkit-scrollbar-track {
    background: transparent;
  }

  &::-webkit-scrollbar-thumb {
    background: transparent;
    border: 2px solid transparent;
    border-radius: 99px;
    background-clip: padding-box;
    transition: background 0.3s ease;
  }

  &:hover {
    /** "-webkit-scrollbar" must be set while using "-webkit-scrollbar-thumb" */
    /** see: https://stackoverflow.com/questions/44212713/styling-webkit-scrollbar-track-not-working */
    &::-webkit-scrollbar {
      width: 10px;
      height: 10px;
    }

    &::-webkit-scrollbar-thumb {
      background-color: ${LEVEL_4};
    }
  }

  &::-webkit-scrollbar-thumb:hover {
    background: ${LEVEL_3};
    background-clip: padding-box;
  }

  &::-webkit-scrollbar-thumb:active {
    background: ${LEVEL_3};
    background-clip: padding-box;
  }
`;

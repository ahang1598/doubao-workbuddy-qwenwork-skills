import styled from 'styled-components';
import {
  LEVEL_1, LEVEL_3,
  RED_0, RED_5,
  CSS_12R_FOOTNOTE, CSS_14R_BODY,
  LINE_LIGHT, RADIUS_S,
} from '@ali/we-design-3';
import { CSS_SCROLLER } from './styles/scroller';

export const PageContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: stretch;
  box-sizing: border-box;
  height: 100vh;
  padding: 16px 20px;
  overflow: hidden;
`;

export const FormArea = styled.div`
  flex: 1;
  ${CSS_SCROLLER}
  padding: 4px;
`;

export const FieldGroup = styled.div`
  margin-bottom: 16px;
`;

export const FieldLabel = styled.label`
  display: block;
  margin-bottom: 8px;
  ${CSS_14R_BODY}
  font-weight: 400;
  color: ${LEVEL_1};
`;

export const RequiredMark = styled.span`
  color: ${RED_5};
`;

export const SummaryBox = styled.div`
  padding: 16px;
  border-radius: 8px;
  border: 1px solid ${LINE_LIGHT};
  margin-bottom: 12px;
`;

export const SummaryTitle = styled.div`
  ${CSS_12R_FOOTNOTE}
  font-weight: 400;
  color: ${LEVEL_1};
  margin-bottom: 8px;
`;

export const SummaryRow = styled.div`
  ${CSS_12R_FOOTNOTE}
  color: ${LEVEL_1};
  margin-bottom: 4px;
`;

export const SummaryLabel = styled.span`
  color: ${LEVEL_3};
`;

export const ErrorBox = styled.div`
  padding: 8px 12px;
  ${CSS_12R_FOOTNOTE}
  color: ${RED_5};
  background-color: ${RED_0};
  border: 1px solid ${RED_0};
  border-radius: ${RADIUS_S};
`;

export const FooterButton = styled.div`
  margin-top: 12px;
  flex-shrink: 0;
`;

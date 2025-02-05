import {Fragment, useEffect} from 'react';
import styled from '@emotion/styled';

import feedbackOnboardingImg from 'sentry-images/spot/feedback-onboarding.svg';

import {LinkButton} from 'sentry/components/button';
import Panel from 'sentry/components/panels/panel';
import {t} from 'sentry/locale';
import {space} from 'sentry/styles/space';
import {trackAnalytics} from 'sentry/utils/analytics';
import useOrganization from 'sentry/utils/useOrganization';

export default function FeedbackSetupPanel() {
  const organization = useOrganization();

  useEffect(() => {
    trackAnalytics('feedback.index-setup-viewed', {
      organization,
    });
  }, [organization]);

  const docsButton = (
    <LinkButton
      external
      href="https://docs.sentry.io/product/user-feedback/setup/"
      priority="primary"
      onClick={() => {
        trackAnalytics('feedback.index-setup-button-clicked', {
          organization,
        });
      }}
    >
      {t('Set Up Now')}
    </LinkButton>
  );

  return (
    <Panel>
      <Container>
        <IlloBox>
          <img src={feedbackOnboardingImg} />
        </IlloBox>
        <StyledBox>
          <Fragment>
            <h3>{t('Introducing the New User Feedback')}</h3>
            <p>
              {t(
                'Allow your users to create bug reports so they can let you know about these sneaky issues right away. Every report will automatically include related replays, tags, and errors, making fixing the issue dead simple.'
              )}
            </p>
            {docsButton}
          </Fragment>
        </StyledBox>
      </Container>
    </Panel>
  );
}

const Container = styled('div')`
  padding: ${space(3)};
  position: relative;

  @media (min-width: ${p => p.theme.breakpoints.small}) {
    display: flex;
    align-items: center;
    flex-direction: row;
    justify-content: center;
    flex-wrap: wrap;
    min-height: 300px;
    max-width: 1000px;
    margin: 0 auto;
  }

  @media (min-width: ${p => p.theme.breakpoints.medium}) {
    min-height: 350px;
  }
`;

const StyledBox = styled('div')`
  min-width: 0;
  z-index: 1;

  @media (min-width: ${p => p.theme.breakpoints.small}) {
    flex: 2;
  }
`;

const IlloBox = styled(StyledBox)`
  position: relative;
  min-height: 100px;
  max-width: 300px;
  min-width: 150px;
  margin: ${space(2)} auto;

  @media (min-width: ${p => p.theme.breakpoints.small}) {
    flex: 1;
    margin: ${space(3)};
    max-width: auto;
  }
`;

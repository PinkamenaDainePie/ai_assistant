'use client';

import React from 'react';
import { mingRailBtn, mingRailShell } from '../../game/ming/mingUiStyles';

type Props = {
  summonOpen: boolean;
  directiveOpen: boolean;
  decreeOpen: boolean;
  issuesOpen: boolean;
  onToggleSummon: () => void;
  onToggleDirective: () => void;
  onToggleDecree: () => void;
  onToggleIssues: () => void;
};

export const MingLeftNav: React.FC<Props> = ({
  summonOpen,
  directiveOpen,
  decreeOpen,
  issuesOpen,
  onToggleSummon,
  onToggleDirective,
  onToggleDecree,
  onToggleIssues,
}) => (
  <div style={{ ...mingRailShell, borderRight: '1px solid rgba(255,215,0,0.2)' }}>
    <button type="button" title="召见大臣" onClick={onToggleSummon} style={mingRailBtn(summonOpen)}>
      召见
    </button>
    <button type="button" title="拟旨草案" onClick={onToggleDirective} style={mingRailBtn(directiveOpen)}>
      拟旨
    </button>
    <button type="button" title="在办局势" onClick={onToggleIssues} style={mingRailBtn(issuesOpen)}>
      局势
    </button>
    <button type="button" title="诏书邸报" onClick={onToggleDecree} style={mingRailBtn(decreeOpen)}>
      邸报
    </button>
  </div>
);

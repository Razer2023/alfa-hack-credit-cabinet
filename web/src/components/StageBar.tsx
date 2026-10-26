import type { ApplicationStatus } from '../api/types';
import { CURRENT_STAGE, STAGES, stageLabel } from '../stages';
import styles from './StageBar.module.css';

type StageBarProps = {
  status: ApplicationStatus;
  // inverted — белые отрезки на тёмном первом экране
  inverted?: boolean;
  className?: string;
};

// Короткий путь заявки: шесть отрезков, пройденные закрашены, текущий — красный
export function StageBar({ status, inverted = false, className }: StageBarProps) {
  const current = CURRENT_STAGE[status];
  const segmentClass = (index: number) => {
    if (status === 'CANCELLED') return styles.segment;
    if (status === 'ISSUED' || index < current - 1) return `${styles.segment} ${styles.done}`;
    return index === current - 1 ? `${styles.segment} ${styles.active}` : styles.segment;
  };

  return (
    <div
      className={[styles.bar, inverted && styles.inverted, className].filter(Boolean).join(' ')}
      role='img'
      aria-label={stageLabel(status)}
    >
      {STAGES.map((stage, index) => <span key={stage.title} className={segmentClass(index)} />)}
    </div>
  );
}

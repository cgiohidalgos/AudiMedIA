import { RiskLevel } from '@/types/audit';

interface RiskBadgeProps {
  level: RiskLevel;
  className?: string;
}

const RiskBadge = ({ level, className = '' }: RiskBadgeProps) => {
  const base = level === 'ALTO'
    ? 'risk-badge-alto'
    : level === 'MEDIO'
      ? 'risk-badge-medio'
      : 'risk-badge-bajo';

  return (
    <span className={`${base} ${className}`} role="status" aria-label={`Riesgo ${level}`}>
      {level === 'ALTO' && '● '}{level === 'MEDIO' && '▲ '}{level === 'BAJO' && '✓ '}
      RIESGO {level}
    </span>
  );
};

export default RiskBadge;

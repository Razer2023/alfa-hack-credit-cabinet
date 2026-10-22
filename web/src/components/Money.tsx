import { Amount } from '@alfalab/core-components/amount';

type MoneyProps = {
  value: number;
  bold?: boolean;
};

// Суммы в API — целые рубли
export function Money({ value, bold = false }: MoneyProps) {
  return <Amount value={value} minority={1} currency='RUB' bold={bold ? 'full' : 'none'} />;
}

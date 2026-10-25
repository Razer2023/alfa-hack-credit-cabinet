import { Plate, type PlateProps } from '@alfalab/core-components/plate';

type CardProps = Omit<PlateProps, 'view' | 'background' | 'border' | 'shadow' | 'rounded' | 'borderRadius'>;

// Основной блок страницы: белая поверхность с мягкой тенью, как карточка заявки и каталог.
// Цветные плашки (решение, отказ, «нужны данные») остаются Plate с view='attention' / 'negative' / 'positive'.
export function Card(props: CardProps) {
  return (
    <Plate
      view='custom'
      background='var(--color-light-base-bg-primary)'
      border={false}
      shadow={true}
      rounded={true}
      borderRadius='var(--border-radius-24)'
      {...props}
    />
  );
}

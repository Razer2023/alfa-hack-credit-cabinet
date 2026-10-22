import type { Offer } from '../../api/types';
import { FactList } from '../../components/FactList';
import { Money } from '../../components/Money';
import { formatMonths } from '../../format';

type OfferFactsProps = {
  offer: Offer;
};

export function OfferFacts({ offer }: OfferFactsProps) {
  return (
    <FactList
      facts={[
        { label: 'Сумма', value: <Money value={offer.amount} bold={true} /> },
        { label: 'Срок', value: formatMonths(offer.term_months) },
        { label: 'Ставка', value: `${offer.rate}% годовых` },
        { label: 'Ежемесячный платёж', value: <Money value={offer.monthly_payment} /> },
      ]}
    />
  );
}

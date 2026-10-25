// Типы ответов ядра. Источник — src/api/schema.d.ts, он генерируется из contracts/core.yaml: npm run gen:api.
import type { components } from './schema';

type Schemas = components['schemas'];

export type User = Schemas['UserOut'];
export type Token = Schemas['TokenOut'];
export type Role = Schemas['Role'];
export type Product = Schemas['ProductOut'];
export type PaymentCalc = Schemas['PaymentCalcOut'];
export type Application = Schemas['ApplicationOut'];
export type BankApplication = Schemas['ApplicationBankOut'];
export type ApplicationStatus = Schemas['ApplicationStatus'];
export type StatusOut = Schemas['StatusOut'];
export type Offer = Schemas['OfferOut'];
export type ApplicationEvent = Schemas['EventOut'];
export type CodeRequest = Schemas['CodeRequestOut'];
export type CompanyField = Schemas['CompanyField'];
export type DataSource = Schemas['DataSource'];
export type ErrorOut = Schemas['ErrorOut'];
export type DecisionIn = Schemas['DecisionIn'];
export type InfoItem = Schemas['InfoItem'];
export type DocumentRequest = Schemas['DocumentRequestOut'];
export type DocumentItem = Schemas['DocumentItemOut'];

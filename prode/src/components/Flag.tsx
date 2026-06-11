import * as Flags from 'country-flag-icons/react/3x2'

// country-flag-icons solo exporta ISO 3166-1 alpha-2 en mayúsculas. La base
// puede traer códigos FIFA de 3 letras (URU, GER…) o alpha-3 (URY, DEU…) si
// el sync auto-creó el equipo, así que normalizamos antes del lookup.
const ALIAS: Record<string, string> = {
  // FIFA TLA → alpha-2 (los 48 clasificados al Mundial 2026)
  MEX: 'MX', RSA: 'ZA', KOR: 'KR', CZE: 'CZ',
  CAN: 'CA', BIH: 'BA', QAT: 'QA', SUI: 'CH',
  BRA: 'BR', MAR: 'MA', HAI: 'HT', SCO: 'GB',
  USA: 'US', PAR: 'PY', AUS: 'AU', TUR: 'TR',
  GER: 'DE', CUW: 'CW', CIV: 'CI', ECU: 'EC',
  NED: 'NL', JPN: 'JP', SWE: 'SE', TUN: 'TN',
  BEL: 'BE', EGY: 'EG', IRN: 'IR', NZL: 'NZ',
  ESP: 'ES', CPV: 'CV', KSA: 'SA', URU: 'UY',
  FRA: 'FR', SEN: 'SN', IRQ: 'IQ', NOR: 'NO',
  ARG: 'AR', ALG: 'DZ', AUT: 'AT', JOR: 'JO',
  POR: 'PT', COD: 'CD', UZB: 'UZ', COL: 'CO',
  ENG: 'GB', CRO: 'HR', GHA: 'GH', PAN: 'PA',
  // ISO 3166-1 alpha-3 que difieren del TLA de FIFA
  URY: 'UY', CHE: 'CH', DEU: 'DE', NLD: 'NL',
  PRY: 'PY', SAU: 'SA', ZAF: 'ZA', DZA: 'DZ', GBR: 'GB',
}

function normalize(codigo: string): string {
  const c = (codigo ?? '').trim().toUpperCase()
  return ALIAS[c] ?? c
}

export default function Flag({ codigo, className }: { codigo: string; className?: string }) {
  const key = normalize(codigo)
  const FlagComp = (Flags as Record<string, React.ComponentType<{ className?: string }> | undefined>)[key]
  if (!FlagComp) {
    // Placeholder visible (el span sin altura era invisible)
    return <span className={`inline-block bg-border rounded-sm aspect-[3/2] ${className ?? 'w-5'}`} />
  }
  return <FlagComp className={className ?? 'w-5 rounded-sm'} />
}

import { PatientCase } from '@/types/audit';

export const mockPatients: PatientCase[] = [
  {
    id: '1',
    label: 'Historia A',
    cama: 'Cama 301',
    diagnosticoPrincipal: 'Neumonía adquirida en comunidad',
    codigoCIE10: 'J18.9',
    diasHospitalizacion: 7,
    diasEsperados: '3-4',
    riesgo: 'ALTO',
    estudiosPendientes: ['TAC tórax (02/03)', 'Hemocultivo (03/03)'],
    hallazgos: [
      { id: 'h1', modulo: 'estancia', descripcion: 'Estancia prolongada: 4 días adicionales sin justificación documentada en evolución médica.', riesgo: 'ALTO', pagina: 15, resuelto: false },
      { id: 'h2', modulo: 'estudios', descripcion: 'TAC de tórax solicitado el 02/03 sin reporte posterior en la historia clínica.', riesgo: 'MEDIO', pagina: 22, resuelto: false },
      { id: 'h3', modulo: 'glosas', descripcion: 'No se encontró evolución médica documentada para el día 05/03.', riesgo: 'ALTO', pagina: undefined, resuelto: false },
      { id: 'h4', modulo: 'cie10', descripcion: 'Diagnóstico J18.9 es consistente con cuadro clínico descrito. CUMPLE.', riesgo: 'BAJO', pagina: 3, resuelto: true },
      { id: 'h5', modulo: 'glosas', descripcion: 'Ceftriaxona 1g IV sin indicación terapéutica documentada en la historia.', riesgo: 'MEDIO', pagina: 18, resuelto: false },
    ],
    recomendaciones: [
      'Solicitar reporte de TAC de tórax del 02/03 al servicio de radiología.',
      'Documentar justificación de estancia adicional en evolución del día 5.',
      'Registrar indicación terapéutica de Ceftriaxona en historia clínica.',
      'Evaluar criterios de egreso: 7 días actuales vs 3-4 esperados.',
    ],
  },
  {
    id: '2',
    label: 'Historia B',
    cama: 'Cama 302',
    diagnosticoPrincipal: 'Apendicitis aguda',
    codigoCIE10: 'K35.2',
    diasHospitalizacion: 2,
    diasEsperados: '3-5',
    riesgo: 'BAJO',
    estudiosPendientes: [],
    hallazgos: [
      { id: 'h6', modulo: 'estancia', descripcion: 'Estancia dentro de rango esperado. Sin alertas.', riesgo: 'BAJO', pagina: 5, resuelto: true },
      { id: 'h7', modulo: 'cie10', descripcion: 'Diagnóstico K35.2 consistente con hallazgos quirúrgicos. CUMPLE.', riesgo: 'BAJO', pagina: 2, resuelto: true },
    ],
    recomendaciones: [
      'Sin hallazgos críticos. Historia clínica completa y documentada.',
    ],
  },
  {
    id: '3',
    label: 'Historia C',
    cama: 'Cama 315',
    diagnosticoPrincipal: 'Infarto agudo de miocardio',
    codigoCIE10: 'I21.0',
    diasHospitalizacion: 5,
    diasEsperados: '5-7',
    riesgo: 'MEDIO',
    estudiosPendientes: ['Ecocardiograma (04/03)', 'Troponinas seriadas (03/03)'],
    hallazgos: [
      { id: 'h8', modulo: 'estudios', descripcion: 'Ecocardiograma solicitado el 04/03 sin reporte en historia.', riesgo: 'MEDIO', pagina: 28, resuelto: false },
      { id: 'h9', modulo: 'estudios', descripcion: 'Troponinas seriadas solicitadas el 03/03, solo primer resultado documentado.', riesgo: 'MEDIO', pagina: 12, resuelto: false },
      { id: 'h10', modulo: 'cie10', descripcion: 'Diagnóstico I21.0 consistente con ECG y clínica. CUMPLE.', riesgo: 'BAJO', pagina: 4, resuelto: true },
      { id: 'h11', modulo: 'glosas', descripcion: 'Evolución médica completa para todos los días de hospitalización.', riesgo: 'BAJO', resuelto: true },
    ],
    recomendaciones: [
      'Solicitar reporte de ecocardiograma al servicio de cardiología.',
      'Completar serie de troponinas con resultados de control.',
      'Verificar estudios complementarios según GPC para IAM.',
    ],
  },
];

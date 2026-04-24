export interface KoruQuestion {
  id: string;
  texto: string;
  tipo: 'opcion_unica_categorizada' | 'abierta_critica';
  opciones?: Array<{
    valor: string;
    etiqueta: string;
    categoria: string[];
  }>;
  placeholder?: string;
}

export interface KoruFase {
  fase_id: string;
  titulo: string;
  descripcion: string;
  preguntas: KoruQuestion[];
}

export interface KoruGenomeTest {
  test_id: string;
  nombre: string;
  version: string;
  fases: KoruFase[];
}

export const KORU_GENOME_V4: KoruGenomeTest = {
  test_id: "KORU-GENOME-v4.0",
  nombre: "El Protocolo del Genoma Maestro",
  version: "4.0",
  fases: [
    {
      fase_id: "F1",
      titulo: "Acto I: Tu Motor Interno",
      descripcion: "Todo viaje inicia con un impulso. ¿Cuál es el tuyo?",
      preguntas: [
        {
          id: "q1",
          texto: "¿Cuál es el objetivo principal de una vida bien vivida?",
          tipo: "opcion_unica_categorizada",
          opciones: [
            { valor: "A", etiqueta: "Ser bueno, íntegro y moralmente correcto.", categoria: ["Eneatipo_1"] },
            { valor: "B", etiqueta: "Ser amado y conectar profundamente.", categoria: ["Eneatipo_2"] },
            { valor: "C", etiqueta: "Ser exitoso y reconocido.", categoria: ["Eneatipo_3"] },
            { valor: "D", etiqueta: "Ser único y fiel a mi identidad.", categoria: ["Eneatipo_4"] },
            { valor: "E", etiqueta: "Ser competente y entender el mundo.", categoria: ["Eneatipo_5"] },
            { valor: "F", etiqueta: "Ser libre y disfrutar la vida.", categoria: ["Eneatipo_7"] }
          ]
        },
        {
          id: "q2",
          texto: "¿Qué pensamiento te genera más ansiedad?",
          tipo: "opcion_unica_categorizada",
          opciones: [
            { valor: "A", etiqueta: "Haber fallado a mi ética o estándar.", categoria: ["Eneatipo_1"] },
            { valor: "B", etiqueta: "Haber decepcionado a quienes dependen de mí.", categoria: ["Eneatipo_2"] },
            { valor: "C", etiqueta: "Ser visto como un fraude.", categoria: ["Eneatipo_3"] },
            { valor: "D", etiqueta: "Sentir que no soy nadie.", categoria: ["Eneatipo_4"] },
            { valor: "E", etiqueta: "No ser lo suficientemente inteligente.", categoria: ["Eneatipo_5"] }
          ]
        },
        {
            id: "q4_critica",
            texto: "Describe tu estado de flow (lo que te hace perder la noción del tiempo).",
            tipo: "abierta_critica",
            placeholder: "Ej: Depurando código, diseñando, creando..."
        }
      ]
    },
    {
        fase_id: "F2",
        titulo: "Acto II: Tu Estilo Cognitivo",
        descripcion: "El mundo te presenta problemas. ¿Cómo los resuelves?",
        preguntas: [
          {
            id: "q5",
            texto: "Ante una idea nueva que contradice tus creencias:",
            tipo: "opcion_unica_categorizada",
            opciones: [
              { valor: "A", etiqueta: "La deconstruyo lógicamente.", categoria: ["Cognicion_Ti"] },
              { valor: "B", etiqueta: "Busco evidencia tangible.", categoria: ["Cognicion_Si"] },
              { valor: "C", etiqueta: "Exploro sus posibilidades futuras.", categoria: ["Cognicion_Ne"] }
            ]
          },
          {
            id: "q6",
            texto: "Al construir algo, ¿qué priorizas?",
            tipo: "opcion_unica_categorizada",
            opciones: [
              { valor: "A", etiqueta: "La visión abstracta y el concepto.", categoria: ["Cognicion_Ni"] },
              { valor: "B", etiqueta: "La experiencia inmediata y sensorial.", categoria: ["Cognicion_Se"] },
              { valor: "C", etiqueta: "El proceso robusto y detallado.", categoria: ["Cognicion_Si"] }
            ]
          },
          {
              id: "q8_critica",
              texto: "Si pudieras dominar una habilidad compleja en 6 meses, ¿cuál sería?",
              tipo: "abierta_critica",
              placeholder: "Tu próximo gran salto evolutivo..."
          }
        ]
      },
      {
        fase_id: "F3",
        titulo: "Acto III: Tu Sombra y Resiliencia",
        descripcion: "El mar se agita. ¿Cómo respondes a la adversidad?",
        preguntas: [
          {
            id: "q9",
            texto: "Ante un estrés intenso, ¿tu reacción automática es?",
            tipo: "opcion_unica_categorizada",
            opciones: [
              { valor: "A", etiqueta: "Me paralizo o rumio el problema.", categoria: ["Alto_Neuroticismo"] },
              { valor: "B", etiqueta: "Actúo de inmediato para solucionarlo.", categoria: ["Bajo_Neuroticismo"] },
              { valor: "C", etiqueta: "Intelectualizo la emoción.", categoria: ["Cognicion_Ti"] }
            ]
          },
          {
              id: "q12_critica",
              texto: "¿Qué 'superpoder' interno usaste para superar tu último gran desafío?",
              tipo: "abierta_critica",
              placeholder: "Esa fortaleza que te define..."
          }
        ]
      },
      {
        fase_id: "F4",
        titulo: "Acto IV: Tu Forma de Conectar",
        descripcion: "¿Cómo te relacionas con los demás?",
        preguntas: [
          {
            id: "q13",
            texto: "En tus relaciones más cercanas:",
            tipo: "opcion_unica_categorizada",
            opciones: [
              { valor: "A", etiqueta: "Necesito mi espacio y autosuficiencia.", categoria: ["Apego_Evitativo"] },
              { valor: "B", etiqueta: "Busco seguridad y cercanía constante.", categoria: ["Apego_Ansioso"] },
              { valor: "C", etiqueta: "Hablo abiertamente de mis necesidades.", categoria: ["Apego_Seguro"] }
            ]
          },
          {
            id: "q16",
            texto: "Tu identidad se define principalmente por:",
            tipo: "opcion_unica_categorizada",
            opciones: [
              { valor: "A", etiqueta: "Mis relaciones y comunidad.", categoria: ["Kegan_3"] },
              { valor: "B", etiqueta: "Mi sistema de valores y carrera.", categoria: ["Kegan_4"] },
              { valor: "C", etiqueta: "Un proceso fluido de cambio.", categoria: ["Kegan_5"] }
            ]
          }
        ]
      },
      {
        fase_id: "F5",
        titulo: "Acto V: Potencial y Legado",
        descripcion: "Miras hacia el horizonte.",
        preguntas: [
          {
            id: "q19",
            texto: "¿Cómo prefieres que tu Aeon se comunique contigo?",
            tipo: "opcion_unica_categorizada",
            opciones: [
              { valor: "Filosofo", etiqueta: "Reflexivo y profundo.", categoria: ["Tono_Filosofo"] },
              { valor: "Coach", etiqueta: "Directo y motivador.", categoria: ["Tono_Coach"] },
              { valor: "Empatico", etiqueta: "Cálido y compasivo.", categoria: ["Tono_Empatico"] },
              { valor: "Logico", etiqueta: "Analítico y al grano.", categoria: ["Tono_Logico"] }
            ]
          },
          {
              id: "q20_critica",
              texto: "Imagina tu cumpleaños 80. ¿Por qué te gustaría ser recordado?",
              tipo: "abierta_critica",
              placeholder: "Tu impacto final..."
          }
        ]
      }
  ]
};

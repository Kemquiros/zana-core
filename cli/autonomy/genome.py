from typing import List, Dict, Any, Optional

KORU_GENOME_V4 = {
    "test_id": "KORU-GENOME-v4.0",
    "nombre": "El Protocolo del Genoma Maestro",
    "version": "4.0",
    "fases": [
        {
            "fase_id": "F1",
            "titulo": "Acto I: La Salida del Puerto (Tu Motor Interno)",
            "descripcion": "Todo viaje inicia con un impulso. ¿Cuál es el tuyo?",
            "preguntas": [
                {
                    "id": "q1",
                    "texto": "Si pudieras definir el 'objetivo principal' de una vida bien vivida, ¿cuál sería?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "Ser bueno, íntegro y moralmente correcto.", "categoria": ["Eneatipo_1", "Valor_Conformidad"] },
                        { "valor": "B", "etiqueta": "Ser amado, necesitado y conectar profundamente.", "categoria": ["Eneatipo_2", "Valor_Benevolencia"] },
                        { "valor": "C", "etiqueta": "Ser exitoso, valioso y reconocido por mis logros.", "categoria": ["Eneatipo_3", "Valor_Poder"] },
                        { "valor": "D", "etiqueta": "Ser único, auténtico y fiel a mi identidad.", "categoria": ["Eneatipo_4", "Valor_Autodireccion"] },
                        { "valor": "E", "etiqueta": "Ser competente, sabio y entender el mundo.", "categoria": ["Eneatipo_5", "Valor_Universalismo"] },
                        { "valor": "F", "etiqueta": "Ser libre, feliz, experimentar todo y evitar el dolor.", "categoria": ["Eneatipo_7", "Valor_Hedonismo"] }
                    ]
                },
                {
                    "id": "q2",
                    "texto": "Imagina tu peor miedo profesional: un proyecto crítico fracasa. ¿Qué pensamiento te atormenta más en la noche?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "'He fallado a mi ética o a mi estándar de perfección'.", "categoria": ["Eneatipo_1"] },
                        { "valor": "B", "etiqueta": "'He decepcionado a la gente que depende de mí'.", "categoria": ["Eneatipo_2"] },
                        { "valor": "C", "etiqueta": "'Todos verán que soy un fraude; he perdido mi valor'.", "categoria": ["Eneatipo_3"] },
                        { "valor": "D", "etiqueta": "'Mi trabajo era mi identidad; ahora no soy nada'.", "categoria": ["Eneatipo_4"] },
                        { "valor": "E", "etiqueta": "'No fui lo suficientemente competente o inteligente'.", "categoria": ["Eneatipo_5"] },
                        { "valor": "F", "etiqueta": "'Esto me deja atrapado y vulnerable, me han controlado'.", "categoria": ["Eneatipo_8"] }
                    ]
                },
                {
                    "id": "q3",
                    "texto": "Después de una semana socialmente intensa, ¿cómo te 'recargas' verdaderamente?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "Soledad absoluta. Silencio, un libro, código o naturaleza.", "categoria": ["Introvertido"] },
                        { "valor": "B", "etiqueta": "Con 1 o 2 personas muy cercanas, en una conversación profunda.", "categoria": ["Ambivertido_Profundo"] },
                        { "valor": "C", "etiqueta": "En un evento social, con música, amigos y energía alta.", "categoria": ["Extravertido"] }
                    ]
                },
                {
                    "id": "q4_critica",
                    "texto": "Describe una actividad en tu vida que te haga perder la noción del tiempo (tu 'estado de flow'). ¿Qué estás haciendo exactamente?",
                    "tipo": "abierta_critica",
                    "placeholder": "Ej: Depurando un bug complejo, debatiendo filosofía, diseñando una UI, tocando guitarra..."
                }
            ]
        },
        {
            "fase_id": "F2",
            "titulo": "Acto II: El Mar Abierto (Tu Estilo Cognitivo)",
            "descripcion": "El mundo te presenta problemas. ¿Cómo los resuelves?",
            "preguntas": [
                {
                    "id": "q5",
                    "texto": "Recibes una idea completamente nueva que contradice tus creencias. ¿Tu reacción inicial?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "Intrigado. La deconstruyo mentalmente para ver si encaja en mi modelo.", "categoria": ["Alta_Apertura", "Cognicion_Ti"] },
                        { "valor": "B", "etiqueta": "Escéptico. Prefiero lo probado y verdadero. ¿Dónde está la evidencia?", "categoria": ["Baja_Apertura", "Cognicion_Si"] },
                        { "valor": "C", "etiqueta": "Emocionado. Pienso en todas las nuevas posibilidades que abre.", "categoria": ["Alta_Apertura", "Cognicion_Ne"] },
                        { "valor": "D", "etiqueta": "Incómodo. Siento que desestabiliza las cosas.", "categoria": ["Baja_Apertura"] }
                    ]
                },
                {
                    "id": "q6",
                    "texto": "Estás construyendo algo. ¿Qué es más importante para ti?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "La visión a largo plazo, el 'por qué' y el concepto abstracto.", "categoria": ["Cognicion_Ni"] },
                        { "valor": "B", "etiqueta": "La experiencia tangible e inmediata. El 'qué' y cómo se siente.", "categoria": ["Cognicion_Se"] },
                        { "valor": "C", "etiqueta": "El proceso y los detalles. Que sea robusto y bien hecho.", "categoria": ["Cognicion_Si", "Alta_Responsabilidad"] },
                        { "valor": "D", "etiqueta": "La exploración de múltiples opciones y la flexibilidad para cambiar.", "categoria": ["Cognicion_Ne", "Baja_Responsabilidad"] }
                    ]
                },
                {
                    "id": "q7",
                    "texto": "Un colega está emocionalmente afectado, pero su lógica es incorrecta y afecta al proyecto. ¿Qué priorizas?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "La Verdad (Thinking). Corrijo la lógica. Los hechos son los hechos.", "categoria": ["Cognicion_T"] },
                        { "valor": "B", "etiqueta": "La Armonía (Feeling). Valido sus sentimientos primero, la lógica después.", "categoria": ["Cognicion_F"] }
                    ]
                },
                {
                    "id": "q8_critica",
                    "texto": "Si tuvieras 6 meses de tiempo y recursos garantizados para dominar UNA nueva habilidad compleja, ¿cuál sería y por qué?",
                    "tipo": "abierta_critica",
                    "placeholder": "Ej: 'Piano nivel concierto', 'Hablar Mandarín fluido', 'Construir un LLM desde cero'..."
                }
            ]
        },
        {
            "fase_id": "F3",
            "titulo": "Acto III: La Tormenta (Tu Sombra y Resiliencia)",
            "descripcion": "El mar se agita. ¿Cómo respondes a la adversidad?",
            "preguntas": [
                {
                    "id": "q9",
                    "texto": "Cuando sientes la primera ola de estrés intenso o ansiedad, ¿cuál es tu reacción automática?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "Me paralizo o evito la fuente del estrés (Rumiación).", "categoria": ["Alto_Neuroticismo"] },
                        { "valor": "B", "etiqueta": "Actúo. Me enfoco en la tarea para solucionarlo (Acción).", "categoria": ["Bajo_Neuroticismo", "Alta_Responsabilidad"] },
                        { "valor": "C", "etiqueta": "Me disocio. Intelectualizo la emoción hasta que desaparece (Análisis).", "categoria": ["Bajo_Neuroticismo", "Cognicion_Ti"] },
                        { "valor": "D", "etiqueta": "Busco a alguien para hablarlo y ventilarlo (Vínculo).", "categoria": ["Alto_Neuroticismo", "Apego_Ansioso"] }
                    ]
                },
                {
                    "id": "q10",
                    "texto": "Has cometido un error tonto que solo tú sabes. ¿Qué te dices a ti mismo?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "'Soy un idiota. No puedo creer que haya hecho eso'. (Crítica)", "categoria": ["Esquema_Defectividad"] },
                        { "valor": "B", "etiqueta": "'Ok, ¿cuál fue el error en el proceso? A analizar y que no se repita'. (Análisis)", "categoria": ["Cognicion_T"] },
                        { "valor": "C", "etiqueta": "'Bueno, todo el mundo se equivoca. No es para tanto'. (Compasión)", "categoria": ["Cognicion_F"] },
                        { "valor": "D", "etiqueta": "Siento una profunda vergüenza y espero que nadie se entere.", "categoria": ["Esquema_Defectividad"] }
                    ]
                },
                {
                    "id": "q11",
                    "texto": "Imagina una creencia central que te ha limitado. ¿Cuál de estas resuena más?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "'Al final, la gente que quiero me abandonará o decepcionará'.", "categoria": ["Esquema_Abandono"] },
                        { "valor": "B", "etiqueta": "'No soy lo suficientemente bueno (inteligente, capaz, etc) y otros sí lo son'.", "categoria": ["Esquema_Defectividad", "Esquema_Fracaso"] },
                        { "valor": "C", "etiqueta": "'No debo depender de nadie; solo puedo confiar en mí mismo'.", "categoria": ["Esquema_Desconfianza", "Apego_Evitativo"] },
                        { "valor": "D", "etiqueta": "'No merezco que me pasen cosas buenas'.", "categoria": ["Esquema_Privacion_Emocional"] },
                        { "valor": "E", "etiqueta": "'El mundo es peligroso y algo malo va a pasar'.", "categoria": ["Esquema_Vulnerabilidad"] }
                    ]
                },
                {
                    "id": "q12_critica",
                    "texto": "Piensa en un desafío difícil que superaste. ¿Qué 'superpoder' interno usaste para lograrlo? Describe esa fortaleza.",
                    "tipo": "abierta_critica",
                    "placeholder": "Ej: 'Mi paciencia', 'Mi lógica fría', 'Mi creatividad para ver otra salida', 'Mi disciplina'..."
                }
            ]
        },
        {
            "fase_id": "F4",
            "titulo": "Acto IV: La Isla (Tu Forma de Conectar)",
            "descripcion": "Llegas a tierra. ¿Cómo te relacionas con sus habitantes?",
            "preguntas": [
                {
                    "id": "q13",
                    "texto": "Tu pareja o amigo más cercano quiere más intimidad emocional de la que te sientes cómodo dando. ¿Tu reacción?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "Me agobio y necesito espacio. Me retiro para procesar.", "categoria": ["Apego_Evitativo"] },
                        { "valor": "B", "etiqueta": "Siento ansiedad. Me esfuerzo más para dársela, temiendo que se aleje.", "categoria": ["Apego_Ansioso"] },
                        { "valor": "C", "etiqueta": "Hablo abiertamente sobre el tema para encontrar un balance.", "categoria": ["Apego_Seguro"] },
                        { "valor": "D", "etiqueta": "Alterno entre necesitar espacio y sentir ansiedad.", "categoria": ["Apego_Desorganizado"] }
                    ]
                },
                {
                    "id": "q14",
                    "texto": "En un debate grupal, ¿qué valoras más?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "La Tradición y el Orden. (Lo que siempre ha funcionado).", "categoria": ["Espiral_Azul"] },
                        { "valor": "B", "etiqueta": "La Eficiencia y el Éxito. (La mejor estrategia para ganar).", "categoria": ["Espiral_Naranja"] },
                        { "valor": "C", "etiqueta": "La Armonía y la Inclusión. (Que todos se sientan escuchados).", "categoria": ["Espiral_Verde"] },
                        { "valor": "D", "etiqueta": "La Verdad Sistémica. (Entender el problema desde todos los ángulos).", "categoria": ["Espiral_Amarillo"] }
                    ]
                },
                {
                    "id": "q15",
                    "texto": "Un colega presenta una idea al equipo que tú sabes que es fundamentalmente errónea. ¿Qué haces?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "Desafiarlo directamente en la reunión. La verdad es lo primero.", "categoria": ["Baja_Amabilidad", "Cognicion_T"] },
                        { "valor": "B", "etiqueta": "No decir nada en público. Hablar con él en privado después.", "categoria": ["Alta_Amabilidad", "Cognicion_F"] },
                        { "valor": "C", "etiqueta": "Hacer preguntas 'socráticas' para que él mismo vea el error.", "categoria": ["Baja_Amabilidad", "Sabio"] }
                    ]
                },
                {
                    "id": "q16",
                    "texto": "Para ti, tu 'identidad' (quién eres) se define principalmente por...",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "Mis relaciones y las expectativas de mi comunidad/familia.", "categoria": ["Kegan_3_Socializado"] },
                        { "valor": "B", "etiqueta": "Mi propio sistema de valores, mi carrera y mi ideología.", "categoria": ["Kegan_4_Auto-Autorizado"] },
                        { "valor": "C", "etiqueta": "Es fluido; soy un 'proceso' que cambia con nueva información.", "categoria": ["Kegan_5_Auto-Transformador"] }
                    ]
                }
            ]
        },
        {
            "fase_id": "F5",
            "titulo": "Acto V: El Horizonte (Tu Potencial y Legado)",
            "descripcion": "Miras hacia el futuro. ¿Qué ves y cómo te guiará tu Aeon?",
            "preguntas": [
                {
                    "id": "q17",
                    "texto": "Mira tu espacio de trabajo (físico o digital) AHORA MISMO. ¿Cómo lo describirías?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "A", "etiqueta": "Minimalista y perfectamente ordenado. Cada cosa en su lugar.", "categoria": ["Alta_Responsabilidad"] },
                        { "valor": "B", "etiqueta": "Funcional. Tiene lo que necesito, pero no está 'ordenado'.", "categoria": ["Media_Responsabilidad"] },
                        { "valor": "C", "etiqueta": "Caos organizado. Sé dónde está todo, pero se ve desordenado.", "categoria": ["Alta_Apertura", "Baja_Responsabilidad"] },
                        { "valor": "D", "etiqueta": "Caos puro. Hay cosas de la semana pasada.", "categoria": ["Baja_Responsabilidad"] }
                    ]
                },
                {
                    "id": "q18",
                    "texto": "Aprendes mejor cuando la información se presenta como...",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "V", "etiqueta": "Diagramas, mapas mentales y videos (Visual)." },
                        { "valor": "A", "etiqueta": "Podcasts, debates y explicaciones habladas (Auditivo)." },
                        { "valor": "R", "etiqueta": "Textos, libros y artículos detallados (Lectura/Escritura)." },
                        { "valor": "K", "etiqueta": "Practicando, experimentando y 'haciendo' (Kinestésico)." }
                    ]
                },
                {
                    "id": "q19",
                    "texto": "¿Cómo prefieres que tu Aeon se comunique contigo?",
                    "tipo": "opcion_unica_categorizada",
                    "opciones": [
                        { "valor": "Filosofo", "etiqueta": "Reflexivo y profundo: '¿Qué significa esto para ti?'" },
                        { "valor": "Coach", "etiqueta": "Directo y motivador: 'Tu objetivo es X. ¡Vamos a por ello!'" },
                        { "valor": "Empatico", "etiqueta": "Amable y compasivo: 'Veo que te sientes así. Está bien.'" },
                        { "valor": "Logico", "etiqueta": "Analítico y al grano: 'La data sugiere que la acción Y es la óptima.'" }
                    ]
                },
                {
                    "id": "q20_critica",
                    "texto": "Imagina tu cumpleaños número 80. En una frase, ¿por qué te gustaría ser celebrado por tus seres queridos?",
                    "tipo": "abierta_critica",
                    "placeholder": "Ej: 'Por el impacto que tuve', 'Por lo bien que amé', 'Por lo que construí', 'Por la sabiduría que compartí'..."
                }
            ]
        }
    ]
}

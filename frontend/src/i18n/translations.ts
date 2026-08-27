/**
 * UI-chrome translations only — English, Hindi, Marathi, Gujarati.
 *
 * This intentionally does NOT translate clinical terminology (NAMASTE terms,
 * ICD-11 titles, definitions). That data is already genuinely multilingual —
 * see app/api.py's native_script fields, sourced straight from the NAMASTE
 * CSVs (Devanagari for Ayurveda, Tamil for Siddha, Arabic for Unani). This
 * file only localizes interface chrome: navigation, page headers, and common
 * action labels — ordinary software-localization vocabulary, not medical
 * claims, so translating it by hand carries none of the mistranslation risk
 * that inventing a clinical-term glossary would.
 */

export type LanguageCode = 'en' | 'hi' | 'mr' | 'gu';

export const LANGUAGES: { code: LanguageCode; label: string; nativeLabel: string }[] = [
  { code: 'en', label: 'English', nativeLabel: 'English' },
  { code: 'hi', label: 'Hindi', nativeLabel: 'हिन्दी' },
  { code: 'mr', label: 'Marathi', nativeLabel: 'मराठी' },
  { code: 'gu', label: 'Gujarati', nativeLabel: 'ગુજરાતી' },
];

type Dict = Record<LanguageCode, string>;

export const translations: Record<string, Dict> = {
  // Sidebar navigation
  nav_overview: { en: 'Overview', hi: 'अवलोकन', mr: 'आढावा', gu: 'ઝાંખી' },
  nav_terminology: { en: 'Terminology Explorer', hi: 'शब्दावली एक्सप्लोरर', mr: 'संज्ञावली एक्सप्लोरर', gu: 'પરિભાષા એક્સપ્લોરર' },
  nav_mapping: { en: 'Mapping Intelligence', hi: 'मैपिंग इंटेलिजेंस', mr: 'मॅपिंग इंटेलिजन्स', gu: 'મેપિંગ ઇન્ટેલિજન્સ' },
  nav_ai_lab: { en: 'AI Mapping Lab', hi: 'एआई मैपिंग लैब', mr: 'एआय मॅपिंग लॅब', gu: 'AI મેપિંગ લેબ' },
  nav_clinical_text: { en: 'Clinical Text Assistant', hi: 'क्लिनिकल टेक्स्ट सहायक', mr: 'क्लिनिकल टेक्स्ट सहाय्यक', gu: 'ક્લિનિકલ ટેક્સ્ટ સહાયક' },
  nav_review_queue: { en: 'Expert Review', hi: 'विशेषज्ञ समीक्षा', mr: 'तज्ज्ञ पुनरावलोकन', gu: 'નિષ્ણાત સમીક્ષા' },
  nav_fhir: { en: 'FHIR Workspace', hi: 'FHIR कार्यक्षेत्र', mr: 'FHIR कार्यक्षेत्र', gu: 'FHIR વર્કસ્પેસ' },
  nav_who_sync: { en: 'WHO Sync', hi: 'WHO सिंक', mr: 'WHO सिंक', gu: 'WHO સિંક' },
  nav_what_if: { en: 'What-If Simulator', hi: 'व्हाट-इफ सिम्युलेटर', mr: 'व्हॉट-इफ सिम्युलेटर', gu: 'વોટ-ઇફ સિમ્યુલેટર' },
  nav_firewall: { en: 'Terminology Firewall', hi: 'टर्मिनोलॉजी फ़ायरवॉल', mr: 'टर्मिनॉलॉजी फायरवॉल', gu: 'ટર્મિનોલોજી ફાયરવોલ' },
  nav_analytics: { en: 'Analytics', hi: 'विश्लेषण', mr: 'विश्लेषण', gu: 'વિશ્લેષણ' },
  nav_developer_portal: { en: 'Developer Portal', hi: 'डेवलपर पोर्टल', mr: 'डेव्हलपर पोर्टल', gu: 'ડેવલપર પોર્ટલ' },
  nav_population_demo: { en: 'Population Health Demo', hi: 'जनसंख्या स्वास्थ्य डेमो', mr: 'लोकसंख्या आरोग्य डेमो', gu: 'વસ્તી આરોગ્ય ડેમો' },
  nav_settings: { en: 'Settings', hi: 'सेटिंग्स', mr: 'सेटिंग्ज', gu: 'સેટિંગ્સ' },

  // Sidebar footer / status
  sidebar_subtitle: { en: 'Interoperability Platform', hi: 'इंटरऑपरेबिलिटी प्लेटफ़ॉर्म', mr: 'इंटरऑपरेबिलिटी प्लॅटफॉर्म', gu: 'ઇન્ટરઓપરેબિલિટી પ્લેટફોર્મ' },
  status_backend_connected: { en: 'Backend Connected', hi: 'बैकएंड कनेक्टेड', mr: 'बॅकएंड कनेक्ट झाले', gu: 'બેકએન્ડ કનેક્ટેડ' },
  status_backend_unreachable: { en: 'Backend Unreachable', hi: 'बैकएंड अनुपलब्ध', mr: 'बॅकएंड अनुपलब्ध', gu: 'બેકએન્ડ અનુપલબ્ધ' },
  status_checking: { en: 'Checking…', hi: 'जाँच हो रही है…', mr: 'तपासत आहे…', gu: 'ચકાસી રહ્યાં છીએ…' },
  status_abha_demo: { en: 'ABHA Demo Mode Auth', hi: 'ABHA डेमो मोड ऑथ', mr: 'ABHA डेमो मोड ऑथ', gu: 'ABHA ડેમો મોડ ઓથ' },
  status_fhir_ready: { en: 'FHIR R4 Gateway Ready', hi: 'FHIR R4 गेटवे तैयार', mr: 'FHIR R4 गेटवे सज्ज', gu: 'FHIR R4 ગેટવે તૈયાર' },

  // Common actions
  action_search: { en: 'Search', hi: 'खोजें', mr: 'शोधा', gu: 'શોધો' },
  action_look_up: { en: 'Look up', hi: 'खोजें', mr: 'पहा', gu: 'જુઓ' },
  action_sync_with_who: { en: 'Sync with WHO', hi: 'WHO के साथ सिंक करें', mr: 'WHO सह सिंक करा', gu: 'WHO સાથે સિંક કરો' },
  action_approve: { en: 'Approve', hi: 'स्वीकृत करें', mr: 'मंजूर करा', gu: 'મંજૂર કરો' },
  action_reject: { en: 'Reject', hi: 'अस्वीकार करें', mr: 'नाकारा', gu: 'નકારો' },
  action_log_out: { en: 'Log out', hi: 'लॉग आउट', mr: 'लॉग आउट', gu: 'લોગ આઉટ' },
  loading: { en: 'Loading…', hi: 'लोड हो रहा है…', mr: 'लोड होत आहे…', gu: 'લોડ થઈ રહ્યું છે…' },

  // Overview page
  page_overview_title: {
    en: 'AYUSH Interoperability Gateway', hi: 'AYUSH इंटरऑपरेबिलिटी गेटवे',
    mr: 'AYUSH इंटरऑपरेबिलिटी गेटवे', gu: 'AYUSH ઇન્ટરઓપરેબિલિટી ગેટવે',
  },
  page_overview_desc: {
    en: 'Intelligent gateway connecting traditional medicine terminology with globally interoperable digital health records.',
    hi: 'पारंपरिक चिकित्सा शब्दावली को वैश्विक रूप से इंटरऑपरेबल डिजिटल स्वास्थ्य रिकॉर्ड से जोड़ने वाला बुद्धिमान गेटवे।',
    mr: 'पारंपरिक औषध संज्ञावलीला जागतिक स्तरावर इंटरऑपरेबल डिजिटल आरोग्य नोंदींशी जोडणारे बुद्धिमान गेटवे.',
    gu: 'પરંપરાગત ચિકિત્સા પરિભાષાને વૈશ્વિક સ્તરે ઇન્ટરઓપરેબલ ડિજિટલ આરોગ્ય રેકોર્ડ સાથે જોડતું બુદ્ધિશાળી ગેટવે.',
  },

  // Terminology Explorer
  page_terminology_title: { en: 'Terminology Explorer', hi: 'शब्दावली एक्सप्लोरर', mr: 'संज्ञावली एक्सप्लोरर', gu: 'પરિભાષા એક્સપ્લોરર' },
  page_terminology_desc: {
    en: 'Explore standardized traditional medicine concepts and their cross-system relationships.',
    hi: 'मानकीकृत पारंपरिक चिकित्सा अवधारणाओं और उनके क्रॉस-सिस्टम संबंधों को खोजें।',
    mr: 'प्रमाणित पारंपरिक औषध संकल्पना आणि त्यांचे क्रॉस-सिस्टम संबंध एक्सप्लोर करा.',
    gu: 'માનકીકૃત પરંપરાગત ચિકિત્સા ખ્યાલો અને તેમના ક્રોસ-સિસ્ટમ સંબંધો શોધો.',
  },
  terminology_search_placeholder: {
    en: 'Search NAMASTE, Ayurveda, Siddha, Unani or ICD-11 terminology…',
    hi: 'NAMASTE, आयुर्वेद, सिद्ध, यूनानी या ICD-11 शब्दावली खोजें…',
    mr: 'NAMASTE, आयुर्वेद, सिद्ध, युनानी किंवा ICD-11 संज्ञावली शोधा…',
    gu: 'NAMASTE, આયુર્વેદ, સિદ્ધ, યુનાની અથવા ICD-11 પરિભાષા શોધો…',
  },

  // Analytics
  page_analytics_title: { en: 'Governance & Interoperability Analytics', hi: 'गवर्नेंस और इंटरऑपरेबिलिटी विश्लेषण', mr: 'गव्हर्नन्स आणि इंटरऑपरेबिलिटी विश्लेषण', gu: 'ગવર્નન્સ અને ઇન્ટરઓપરેબિલિટી વિશ્લેષણ' },

  // WHO Sync
  page_who_sync_title: { en: 'WHO ICD-11 Synchronisation', hi: 'WHO ICD-11 सिंक्रोनाइज़ेशन', mr: 'WHO ICD-11 सिंक्रोनायझेशन', gu: 'WHO ICD-11 સિંક્રોનાઇઝેશન' },


  // ── Page titles and descriptions (every page) ──────────────────────────
  // Technical body copy (FHIR/ICD jargon, API detail) is deliberately left
  // in English: those terms are used in English by Indian clinical software
  // and standards documents, and machine-translating them would reduce
  // clarity rather than improve it.
  page_ai_lab_title: { en: 'AI Mapping Lab', hi: 'एआई मैपिंग लैब', mr: 'एआय मॅपिंग लॅब', gu: 'AI મેપિંગ લેબ' },
  page_ai_lab_desc: {
    en: 'Ambiguity-aware AI suggestions for unmapped NAMASTE codes, with an explicit refusal when confidence is too low.',
    hi: 'अमैप्ड NAMASTE कोड के लिए संदिग्धता-सचेत एआई सुझाव, कम विश्वास होने पर स्पष्ट अस्वीकृति के साथ।',
    mr: 'मॅप न झालेल्या NAMASTE कोडसाठी संदिग्धता-जाणकार एआय सूचना, विश्वास कमी असल्यास स्पष्ट नकारासह.',
    gu: 'અનમેપ્ડ NAMASTE કોડ માટે અસ્પષ્ટતા-જાગૃત AI સૂચનો, વિશ્વાસ ઓછો હોય ત્યારે સ્પષ્ટ ઇનકાર સાથે.',
  },
  page_mapping_title: { en: 'Mapping Intelligence', hi: 'मैपिंग इंटेलिजेंस', mr: 'मॅपिंग इंटेलिजन्स', gu: 'મેપિંગ ઇન્ટેલિજન્સ' },
  page_mapping_desc: {
    en: 'Browse and filter every curated NAMASTE to ICD-11 mapping, with backend-computed confidence.',
    hi: 'बैकएंड-गणित विश्वास के साथ हर क्यूरेटेड NAMASTE से ICD-11 मैपिंग देखें और फ़िल्टर करें।',
    mr: 'बॅकएंड-गणित विश्वासासह प्रत्येक क्युरेटेड NAMASTE ते ICD-11 मॅपिंग पहा आणि फिल्टर करा.',
    gu: 'બેકએન્ડ-ગણતરી કરેલ વિશ્વાસ સાથે દરેક ક્યુરેટેડ NAMASTE થી ICD-11 મેપિંગ બ્રાઉઝ કરો અને ફિલ્ટર કરો.',
  },
  page_review_title: { en: 'Expert Review Queue', hi: 'विशेषज्ञ समीक्षा कतार', mr: 'तज्ज्ञ पुनरावलोकन रांग', gu: 'નિષ્ણાત સમીક્ષા કતાર' },
  page_review_desc: {
    en: 'Human-in-the-loop governance: AI suggestions that need context or expert review land here. Approving one writes a brand-new curated mapping — nothing is ever auto-approved.',
    hi: 'मानव-सहित शासन: जिन एआई सुझावों को संदर्भ या विशेषज्ञ समीक्षा चाहिए वे यहाँ आते हैं। स्वीकृति एक नई क्यूरेटेड मैपिंग बनाती है — कुछ भी स्वतः स्वीकृत नहीं होता।',
    mr: 'मानव-सहभागी शासन: ज्या एआय सूचनांना संदर्भ किंवा तज्ज्ञ पुनरावलोकन आवश्यक आहे त्या इथे येतात. मंजुरी नवीन क्युरेटेड मॅपिंग तयार करते — काहीही आपोआप मंजूर होत नाही.',
    gu: 'માનવ-સહભાગી શાસન: જે AI સૂચનોને સંદર્ભ અથવા નિષ્ણાત સમીક્ષાની જરૂર છે તે અહીં આવે છે. મંજૂરી નવું ક્યુરેટેડ મેપિંગ બનાવે છે — કંઈપણ આપોઆપ મંજૂર થતું નથી.',
  },
  page_fhir_title: { en: 'FHIR Workspace', hi: 'FHIR कार्यक्षेत्र', mr: 'FHIR कार्यक्षेत्र', gu: 'FHIR વર્કસ્પેસ' },
  page_fhir_desc: {
    en: 'Live FHIR R4 operations — $translate, Bundle upload, and ProblemList construction against the real backend.',
    hi: 'लाइव FHIR R4 संचालन — असली बैकएंड पर $translate, Bundle अपलोड और ProblemList निर्माण।',
    mr: 'थेट FHIR R4 क्रिया — खऱ्या बॅकएंडवर $translate, Bundle अपलोड आणि ProblemList निर्मिती.',
    gu: 'લાઇવ FHIR R4 કામગીરી — વાસ્તવિક બેકએન્ડ પર $translate, Bundle અપલોડ અને ProblemList નિર્માણ.',
  },
  page_clinical_text_title: { en: 'Clinical Text Assistant', hi: 'क्लिनिकल टेक्स्ट सहायक', mr: 'क्लिनिकल टेक्स्ट सहाय्यक', gu: 'ક્લિનિકલ ટેક્સ્ટ સહાયક' },
  page_clinical_text_desc: {
    en: 'Describe what the patient reported in plain language. This extracts symptoms, duration, body site and negation, then searches real NAMASTE and ICD-11 terminology. It never infers a diagnosis.',
    hi: 'रोगी ने जो बताया उसे सामान्य भाषा में लिखें। यह लक्षण, अवधि, शरीर-स्थान और निषेध निकालता है, फिर वास्तविक NAMASTE और ICD-11 शब्दावली खोजता है। यह कभी निदान नहीं लगाता।',
    mr: 'रुग्णाने काय सांगितले ते साध्या भाषेत लिहा. हे लक्षणे, कालावधी, शरीर-स्थान आणि नकार ओळखते, नंतर खरी NAMASTE आणि ICD-11 संज्ञावली शोधते. हे कधीही निदान करत नाही.',
    gu: 'દર્દીએ જે જણાવ્યું તે સામાન્ય ભાષામાં લખો. આ લક્ષણો, સમયગાળો, શરીર-સ્થાન અને નકાર ઓળખે છે, પછી વાસ્તવિક NAMASTE અને ICD-11 પરિભાષા શોધે છે. તે ક્યારેય નિદાન કરતું નથી.',
  },
  page_what_if_title: { en: 'Terminology What-If Simulator', hi: 'शब्दावली व्हाट-इफ सिम्युलेटर', mr: 'संज्ञावली व्हॉट-इफ सिम्युलेटर', gu: 'પરિભાષા વોટ-ઇફ સિમ્યુલેટર' },
  page_what_if_desc: {
    en: 'Compare any two real WHO ICD-11 releases and see exactly which curated mappings would break — before the release ships.',
    hi: 'किन्हीं दो वास्तविक WHO ICD-11 रिलीज़ की तुलना करें और देखें कौन-सी क्यूरेटेड मैपिंग टूटेंगी — रिलीज़ आने से पहले।',
    mr: 'कोणत्याही दोन खऱ्या WHO ICD-11 रिलीजची तुलना करा आणि कोणती क्युरेटेड मॅपिंग तुटतील ते पहा — रिलीज येण्यापूर्वी.',
    gu: 'કોઈપણ બે વાસ્તવિક WHO ICD-11 રિલીઝની તુલના કરો અને કઈ ક્યુરેટેડ મેપિંગ તૂટશે તે જુઓ — રિલીઝ આવે તે પહેલાં.',
  },
  page_firewall_title: { en: 'Terminology Firewall', hi: 'टर्मिनोलॉजी फ़ायरवॉल', mr: 'टर्मिनॉलॉजी फायरवॉल', gu: 'ટર્મિનોલોજી ફાયરવોલ' },
  page_firewall_desc: {
    en: 'A clinical terminology quality gateway for external EMRs — returns one accept, reject or review verdict for an incoming FHIR Bundle. It is advisory and never modifies your record.',
    hi: 'बाहरी EMR के लिए क्लिनिकल शब्दावली गुणवत्ता गेटवे — आने वाले FHIR Bundle के लिए एक स्वीकार, अस्वीकार या समीक्षा निर्णय देता है। यह सलाहकारी है और आपका रिकॉर्ड कभी नहीं बदलता।',
    mr: 'बाह्य EMR साठी क्लिनिकल संज्ञावली गुणवत्ता गेटवे — येणाऱ्या FHIR Bundle साठी एक स्वीकार, नकार किंवा पुनरावलोकन निर्णय देते. हे सल्लागार आहे आणि तुमची नोंद कधीही बदलत नाही.',
    gu: 'બાહ્ય EMR માટે ક્લિનિકલ પરિભાષા ગુણવત્તા ગેટવે — આવનારા FHIR Bundle માટે એક સ્વીકાર, નકાર અથવા સમીક્ષા ચુકાદો આપે છે. તે સલાહકારી છે અને તમારો રેકોર્ડ ક્યારેય બદલતું નથી.',
  },
  page_population_title: { en: 'Population Health Demo', hi: 'जनसंख्या स्वास्थ्य डेमो', mr: 'लोकसंख्या आरोग्य डेमो', gu: 'વસ્તી આરોગ્ય ડેમો' },
  page_population_desc: {
    en: 'An illustration of what a national AYUSH population-health view could look like at realistic volume — gender, region and time breakdowns for a Ministry stakeholder to picture.',
    hi: 'यह दर्शाता है कि वास्तविक पैमाने पर राष्ट्रीय AYUSH जनसंख्या-स्वास्थ्य दृश्य कैसा दिख सकता है — लिंग, क्षेत्र और समय के विभाजन के साथ।',
    mr: 'वास्तविक प्रमाणात राष्ट्रीय AYUSH लोकसंख्या-आरोग्य दृश्य कसे दिसू शकते याचे उदाहरण — लिंग, प्रदेश आणि वेळेच्या विभाजनांसह.',
    gu: 'વાસ્તવિક સ્તરે રાષ્ટ્રીય AYUSH વસ્તી-આરોગ્ય દૃશ્ય કેવું દેખાઈ શકે તેનું ઉદાહરણ — લિંગ, પ્રદેશ અને સમયના વિભાજન સાથે.',
  },
  page_developer_title: { en: 'Developer Portal', hi: 'डेवलपर पोर्टल', mr: 'डेव्हलपर पोर्टल', gu: 'ડેવલપર પોર્ટલ' },
  page_developer_desc: {
    en: 'The credential system an external EMR integrates against — separate from clinician login. Generate a key, call the versioned API, and see scopes and rate limits enforced live.',
    hi: 'वह क्रेडेंशियल प्रणाली जिससे बाहरी EMR जुड़ता है — चिकित्सक लॉगिन से अलग। कुंजी बनाएं, संस्करण API कॉल करें, और स्कोप व दर-सीमा लागू होते देखें।',
    mr: 'बाह्य EMR ज्याच्याशी जोडले जाते ती क्रेडेन्शियल प्रणाली — डॉक्टर लॉगिनपासून वेगळी. की तयार करा, आवृत्ती API कॉल करा आणि स्कोप व दर-मर्यादा लागू होताना पहा.',
    gu: 'બાહ્ય EMR જેની સાથે જોડાય છે તે ક્રેડેન્શિયલ સિસ્ટમ — ક્લિનિશિયન લોગિનથી અલગ. કી બનાવો, વર્ઝન કરેલ API કૉલ કરો, અને સ્કોપ અને દર-મર્યાદા લાગુ થતી જુઓ.',
  },
  page_settings_title: { en: 'Settings', hi: 'सेटिंग्स', mr: 'सेटिंग्ज', gu: 'સેટિંગ્સ' },
  page_settings_desc: {
    en: 'Session identity, configured backend, and connected terminology systems.',
    hi: 'सत्र पहचान, कॉन्फ़िगर किया गया बैकएंड, और जुड़े हुए शब्दावली सिस्टम।',
    mr: 'सत्र ओळख, कॉन्फिगर केलेले बॅकएंड आणि जोडलेल्या संज्ञावली प्रणाली.',
    gu: 'સત્ર ઓળખ, ગોઠવેલ બેકએન્ડ, અને જોડાયેલ પરિભાષા સિસ્ટમો.',
  },
  page_who_sync_desc: {
    en: 'The live half of this service: it authenticates against WHO\u2019s ICD-API, resolves codes through it, and reports drift. Nothing is rewritten automatically.',
    hi: 'इस सेवा का लाइव भाग: यह WHO के ICD-API से प्रमाणित होता है, कोड हल करता है, और परिवर्तन बताता है। कुछ भी स्वतः नहीं बदला जाता।',
    mr: 'या सेवेचा थेट भाग: तो WHO च्या ICD-API शी प्रमाणित होतो, कोड सोडवतो आणि बदल नोंदवतो. काहीही आपोआप बदलले जात नाही.',
    gu: 'આ સેવાનો લાઇવ ભાગ: તે WHO ના ICD-API સાથે પ્રમાણિત થાય છે, કોડ ઉકેલે છે, અને ફેરફાર જણાવે છે. કંઈપણ આપોઆપ ફરીથી લખાતું નથી.',
  },
  page_analytics_desc: {
    en: 'A live, oversight-level view of the terminology bridge: corpus size and mapping coverage per AYUSH tradition, the human review backlog, WHO synchronisation posture, and real system activity.',
    hi: 'शब्दावली सेतु का लाइव, निगरानी-स्तरीय दृश्य: प्रत्येक AYUSH परंपरा का संग्रह आकार और मैपिंग कवरेज, मानव समीक्षा बैकलॉग, WHO सिंक स्थिति, और वास्तविक सिस्टम गतिविधि।',
    mr: 'संज्ञावली सेतूचे थेट, देखरेख-स्तरीय दृश्य: प्रत्येक AYUSH परंपरेचा संग्रह आकार आणि मॅपिंग व्याप्ती, मानवी पुनरावलोकन अनुशेष, WHO सिंक स्थिती आणि खरी प्रणाली क्रिया.',
    gu: 'પરિભાષા સેતુનું લાઇવ, દેખરેખ-સ્તરીય દૃશ્ય: દરેક AYUSH પરંપરાનું સંગ્રહ કદ અને મેપિંગ કવરેજ, માનવ સમીક્ષા બેકલોગ, WHO સિંક સ્થિતિ, અને વાસ્તવિક સિસ્ટમ પ્રવૃત્તિ.',
  },

  // Language switcher itself
  language_switcher_label: { en: 'Language', hi: 'भाषा', mr: 'भाषा', gu: 'ભાષા' },
};

export function translate(key: string, lang: LanguageCode): string {
  const entry = translations[key];
  if (!entry) return key;
  return entry[lang] || entry.en;
}

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

  // Language switcher itself
  language_switcher_label: { en: 'Language', hi: 'भाषा', mr: 'भाषा', gu: 'ભાષા' },
};

export function translate(key: string, lang: LanguageCode): string {
  const entry = translations[key];
  if (!entry) return key;
  return entry[lang] || entry.en;
}

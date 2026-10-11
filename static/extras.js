(function () {
  /* ---------- styles ---------- */
  const css = `
  .why{background:#fff7ed;border:1px solid #fed7aa;border-radius:12px;padding:12px;margin-top:8px;font-size:13px;color:#9a3412}
  .why-row{display:flex;justify-content:space-between;align-items:center;gap:10px;border-top:1px dashed #fdba74;padding:8px 0;margin-top:8px;color:#0f172a}
  #sw-dock{position:fixed;right:16px;bottom:16px;z-index:300;display:flex;gap:8px;align-items:center;background:#0b1b3f;padding:8px 10px;border-radius:14px;box-shadow:0 12px 30px rgba(0,0,0,.35)}
  #sw-dock select,#sw-dock button{font:inherit;font-size:13px;font-weight:600;border-radius:9px;border:1px solid rgba(255,255,255,.25);background:rgba(255,255,255,.1);color:#fff;padding:7px 10px;cursor:pointer}
  #sw-dock select option{color:#000}
  #sw-dock .em{background:#dc2626;border-color:#dc2626}
  #sw-dock .em.on{background:#16a34a;border-color:#16a34a}
  #sw-banner{position:sticky;top:0;z-index:400;background:linear-gradient(90deg,#b91c1c,#dc2626);color:#fff;text-align:center;padding:9px;font-weight:700;letter-spacing:.04em;animation:swp 1.4s infinite}
  @keyframes swp{50%{opacity:.82}}
  #sw-guide{display:none;position:fixed;inset:0;background:rgba(15,23,42,.6);z-index:500;align-items:center;justify-content:center;padding:20px}
  #sw-guide.open{display:flex}
  #sw-guide .box{background:#fff;border-radius:16px;max-width:620px;width:100%;max-height:90vh;overflow:auto;padding:24px;color:#0f172a}
  #sw-guide h3{margin-bottom:12px}
  #sw-guide ol{padding-left:20px;display:grid;gap:10px;line-height:1.5}
  #sw-guide .x2{float:right;background:none;border:none;font-size:22px;cursor:pointer}
  `;
  const st = document.createElement('style'); st.textContent = css; document.head.appendChild(st);

  /* ---------- translations ---------- */
  const T = {
    hi: {
      "Live Dashboard": "लाइव डैशबोर्ड", "Schedule & Shifts": "शेड्यूल और शिफ्ट", "Shift Swaps": "शिफ्ट अदला-बदली",
      "Conflicts & Gaps": "टकराव और कमी", "Conflicts & Staffing Gaps": "टकराव और स्टाफ की कमी", "My Portal": "मेरा पोर्टल",
      "Employees": "कर्मचारी", "Absences": "अनुपस्थिति", "Training": "प्रशिक्षण", "Training Academy": "प्रशिक्षण अकादमी",
      "Skill Matrix": "कौशल मैट्रिक्स", "Stress Simulator": "स्ट्रेस सिम्युलेटर", "Published Schedule": "प्रकाशित शेड्यूल",
      "Logout": "लॉग आउट", "Sign out": "साइन आउट", "Reset": "रीसेट",
      "Run Auto-Assign": "ऑटो-असाइन चलाएं", "Auto-Assign All": "सभी ऑटो-असाइन करें", "Auto-Fill Gaps": "कमी ऑटो-भरें",
      "Export Roster (CSV)": "रोस्टर निर्यात (CSV)", "Export CSV": "CSV निर्यात", "Publish Schedule": "शेड्यूल प्रकाशित करें",
      "Create Shift": "शिफ्ट बनाएं", "Assign": "असाइन करें", "Delete shift": "शिफ्ट हटाएं",
      "Resilience Index": "लचीलापन सूचकांक", "Staffing Shortages": "स्टाफ की कमी", "Active Conflicts": "सक्रिय टकराव",
      "Active Staff Pool": "सक्रिय स्टाफ", "Burnout Risk": "बर्नआउट जोखिम", "Burnout Watch": "बर्नआउट निगरानी",
      "Shift Coverage by Day": "दिन अनुसार शिफ्ट कवरेज", "Department Staffing": "विभाग स्टाफिंग",
      "Conflict & Compliance Monitor": "टकराव और अनुपालन मॉनिटर", "Live Demo Controls": "लाइव डेमो नियंत्रण",
      "Inject demo conflicts": "डेमो टकराव डालें", "One-Click Repair": "वन-क्लिक मरम्मत",
      "Department": "विभाग", "Status": "स्थिति", "Date": "तारीख", "Start": "शुरू", "End": "अंत", "Headcount": "संख्या",
      "Priority": "प्राथमिकता", "Shift title": "शिफ्ट का नाम", "Required skill": "आवश्यक कौशल",
      "ASSIGNED": "असाइन किए गए", "SUGGESTED (ranked)": "सुझाव (क्रमबद्ध)", "Nobody assigned yet.": "अभी कोई असाइन नहीं।",
      "Manage / manual assign": "प्रबंधन / मैन्युअल असाइन", "Type": "प्रकार", "Severity": "गंभीरता", "Employee": "कर्मचारी",
      "Shift": "शिफ्ट", "Issue": "समस्या", "Unassign": "हटाएं", "Advisory": "सलाह", "Double booking": "डबल बुकिंग",
      "Rest violation": "आराम उल्लंघन", "Weekly overtime": "साप्ताहिक ओवरटाइम", "Skill mismatch": "कौशल बेमेल",
      "Expired certification": "समाप्त प्रमाणपत्र", "Unavailable day": "अनुपलब्ध दिन", "Absent": "अनुपस्थित", "On leave": "छुट्टी पर",
      "Consecutive days": "लगातार दिन", "Excess daily hours": "अधिक दैनिक घंटे", "Night-shift load": "रात्रि शिफ्ट भार",
      "Cert expiring soon": "प्रमाणपत्र जल्द समाप्त",
      "Hi,": "नमस्ते,", "Mark me absent": "मुझे अनुपस्थित करें", "Ask a colleague to swap": "सहकर्मी से अदला-बदली माँगें",
      "My upcoming shifts": "मेरी आगामी शिफ्ट", "Swaps I requested": "मेरे द्वारा माँगी अदला-बदली",
      "Requests I received": "मुझे मिले अनुरोध", "My absences": "मेरी अनुपस्थिति", "My availability & skills": "मेरी उपलब्धता और कौशल",
      "Save availability": "उपलब्धता सहेजें", "My notifications": "मेरी सूचनाएं", "Mark all read": "सब पढ़ा हुआ करें",
      "Accept": "स्वीकार करें", "Decline": "अस्वीकार करें", "Approve": "मंज़ूर करें", "Reject": "अस्वीकार करें",
      "Notification log": "सूचना लॉग", "Peer-to-peer swap workflow": "सहकर्मी अदला-बदली प्रक्रिया",
      "Send request to colleague": "सहकर्मी को अनुरोध भेजें", "Waiting for colleague": "सहकर्मी के उत्तर की प्रतीक्षा",
      "Awaiting manager approval": "प्रबंधक की मंज़ूरी बाकी", "Completed / closed": "पूर्ण / बंद",
      "Swap Guide": "अदला-बदली गाइड", "EMERGENCY": "आपातकाल", "Emergency ON": "आपातकाल चालू", "Emergency OFF": "आपातकाल बंद",
      "Language": "भाषा", "Close": "बंद करें"
    },
    kn: {
      "Live Dashboard": "ಲೈವ್ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", "Schedule & Shifts": "ವೇಳಾಪಟ್ಟಿ ಮತ್ತು ಶಿಫ್ಟ್", "Shift Swaps": "ಶಿಫ್ಟ್ ಬದಲಾವಣೆ",
      "Conflicts & Gaps": "ಸಂಘರ್ಷ ಮತ್ತು ಕೊರತೆ", "Conflicts & Staffing Gaps": "ಸಂಘರ್ಷ ಮತ್ತು ಸಿಬ್ಬಂದಿ ಕೊರತೆ", "My Portal": "ನನ್ನ ಪೋರ್ಟಲ್",
      "Employees": "ಉದ್ಯೋಗಿಗಳು", "Absences": "ಗೈರುಹಾಜರಿ", "Training": "ತರಬೇತಿ", "Training Academy": "ತರಬೇತಿ ಅಕಾಡೆಮಿ",
      "Skill Matrix": "ಕೌಶಲ್ಯ ಮ್ಯಾಟ್ರಿಕ್ಸ್", "Stress Simulator": "ಒತ್ತಡ ಸಿಮ್ಯುಲೇಟರ್", "Published Schedule": "ಪ್ರಕಟಿತ ವೇಳಾಪಟ್ಟಿ",
      "Logout": "ಲಾಗ್ ಔಟ್", "Sign out": "ಸೈನ್ ಔಟ್", "Reset": "ರೀಸೆಟ್",
      "Run Auto-Assign": "ಆಟೋ-ಅಸೈನ್ ಚಲಾಯಿಸಿ", "Auto-Assign All": "ಎಲ್ಲವನ್ನೂ ಆಟೋ-ಅಸೈನ್", "Auto-Fill Gaps": "ಕೊರತೆ ಆಟೋ-ತುಂಬಿ",
      "Export Roster (CSV)": "ರೋಸ್ಟರ್ ರಫ್ತು (CSV)", "Export CSV": "CSV ರಫ್ತು", "Publish Schedule": "ವೇಳಾಪಟ್ಟಿ ಪ್ರಕಟಿಸಿ",
      "Create Shift": "ಶಿಫ್ಟ್ ರಚಿಸಿ", "Assign": "ನಿಯೋಜಿಸಿ", "Delete shift": "ಶಿಫ್ಟ್ ಅಳಿಸಿ",
      "Resilience Index": "ಸ್ಥಿತಿಸ್ಥಾಪಕತ್ವ ಸೂಚ್ಯಂಕ", "Staffing Shortages": "ಸಿಬ್ಬಂದಿ ಕೊರತೆ", "Active Conflicts": "ಸಕ್ರಿಯ ಸಂಘರ್ಷಗಳು",
      "Active Staff Pool": "ಸಕ್ರಿಯ ಸಿಬ್ಬಂದಿ", "Burnout Risk": "ಬರ್ನ್‌ಔಟ್ ಅಪಾಯ", "Burnout Watch": "ಬರ್ನ್‌ಔಟ್ ಮೇಲ್ವಿಚಾರಣೆ",
      "Shift Coverage by Day": "ದಿನವಾರು ಶಿಫ್ಟ್ ವ್ಯಾಪ್ತಿ", "Department Staffing": "ವಿಭಾಗ ಸಿಬ್ಬಂದಿ",
      "Conflict & Compliance Monitor": "ಸಂಘರ್ಷ ಮತ್ತು ಅನುಸರಣೆ ಮಾನಿಟರ್", "Live Demo Controls": "ಲೈವ್ ಡೆಮೊ ನಿಯಂತ್ರಣ",
      "Inject demo conflicts": "ಡೆಮೊ ಸಂಘರ್ಷ ಸೇರಿಸಿ", "One-Click Repair": "ಒಂದು-ಕ್ಲಿಕ್ ದುರಸ್ತಿ",
      "Department": "ವಿಭಾಗ", "Status": "ಸ್ಥಿತಿ", "Date": "ದಿನಾಂಕ", "Start": "ಪ್ರಾರಂಭ", "End": "ಅಂತ್ಯ", "Headcount": "ಸಂಖ್ಯೆ",
      "Priority": "ಆದ್ಯತೆ", "Shift title": "ಶಿಫ್ಟ್ ಹೆಸರು", "Required skill": "ಅಗತ್ಯ ಕೌಶಲ್ಯ",
      "ASSIGNED": "ನಿಯೋಜಿತರು", "SUGGESTED (ranked)": "ಸಲಹೆ (ಶ್ರೇಣೀಕೃತ)", "Nobody assigned yet.": "ಇನ್ನೂ ಯಾರೂ ನಿಯೋಜಿತರಿಲ್ಲ.",
      "Manage / manual assign": "ನಿರ್ವಹಣೆ / ಹಸ್ತಚಾಲಿತ ನಿಯೋಜನೆ", "Type": "ಪ್ರಕಾರ", "Severity": "ತೀವ್ರತೆ", "Employee": "ಉದ್ಯೋಗಿ",
      "Shift": "ಶಿಫ್ಟ್", "Issue": "ಸಮಸ್ಯೆ", "Unassign": "ತೆಗೆದುಹಾಕಿ", "Advisory": "ಸಲಹೆ", "Double booking": "ಡಬಲ್ ಬುಕಿಂಗ್",
      "Rest violation": "ವಿಶ್ರಾಂತಿ ಉಲ್ಲಂಘನೆ", "Weekly overtime": "ವಾರದ ಓವರ್‌ಟೈಮ್", "Skill mismatch": "ಕೌಶಲ್ಯ ಹೊಂದಾಣಿಕೆಯಿಲ್ಲ",
      "Expired certification": "ಅವಧಿ ಮುಗಿದ ಪ್ರಮಾಣಪತ್ರ", "Unavailable day": "ಲಭ್ಯವಿಲ್ಲದ ದಿನ", "Absent": "ಗೈರು", "On leave": "ರಜೆಯಲ್ಲಿ",
      "Consecutive days": "ನಿರಂತರ ದಿನಗಳು", "Excess daily hours": "ಹೆಚ್ಚುವರಿ ದೈನಂದಿನ ಗಂಟೆ", "Night-shift load": "ರಾತ್ರಿ ಶಿಫ್ಟ್ ಹೊರೆ",
      "Cert expiring soon": "ಪ್ರಮಾಣಪತ್ರ ಶೀಘ್ರ ಮುಗಿಯಲಿದೆ",
      "Hi,": "ನಮಸ್ಕಾರ,", "Mark me absent": "ನನ್ನನ್ನು ಗೈರು ಎಂದು ಗುರುತಿಸಿ", "Ask a colleague to swap": "ಸಹೋದ್ಯೋಗಿಯನ್ನು ಬದಲಾವಣೆ ಕೇಳಿ",
      "My upcoming shifts": "ನನ್ನ ಮುಂಬರುವ ಶಿಫ್ಟ್‌ಗಳು", "Swaps I requested": "ನಾನು ಕೇಳಿದ ಬದಲಾವಣೆಗಳು",
      "Requests I received": "ನನಗೆ ಬಂದ ಮನವಿಗಳು", "My absences": "ನನ್ನ ಗೈರುಹಾಜರಿ", "My availability & skills": "ನನ್ನ ಲಭ್ಯತೆ ಮತ್ತು ಕೌಶಲ್ಯ",
      "Save availability": "ಲಭ್ಯತೆ ಉಳಿಸಿ", "My notifications": "ನನ್ನ ಅಧಿಸೂಚನೆಗಳು", "Mark all read": "ಎಲ್ಲವನ್ನೂ ಓದಿದೆ ಎಂದು ಗುರುತಿಸಿ",
      "Accept": "ಒಪ್ಪಿಕೊಳ್ಳಿ", "Decline": "ನಿರಾಕರಿಸಿ", "Approve": "ಅನುಮೋದಿಸಿ", "Reject": "ತಿರಸ್ಕರಿಸಿ",
      "Notification log": "ಅಧಿಸೂಚನೆ ಲಾಗ್", "Peer-to-peer swap workflow": "ಸಹೋದ್ಯೋಗಿ ಬದಲಾವಣೆ ಪ್ರಕ್ರಿಯೆ",
      "Send request to colleague": "ಸಹೋದ್ಯೋಗಿಗೆ ಮನವಿ ಕಳುಹಿಸಿ", "Waiting for colleague": "ಸಹೋದ್ಯೋಗಿಯ ಉತ್ತರಕ್ಕೆ ಕಾಯುತ್ತಿದೆ",
      "Awaiting manager approval": "ಮ್ಯಾನೇಜರ್ ಅನುಮೋದನೆ ಬಾಕಿ", "Completed / closed": "ಪೂರ್ಣ / ಮುಚ್ಚಲಾಗಿದೆ",
      "Swap Guide": "ಶಿಫ್ಟ್ ಬದಲಾವಣೆ ಮಾರ್ಗದರ್ಶಿ", "EMERGENCY": "ತುರ್ತು ಪರಿಸ್ಥಿತಿ", "Emergency ON": "ತುರ್ತು ಚಾಲನೆ", "Emergency OFF": "ತುರ್ತು ಸ್ಥಗಿತ",
      "Language": "ಭಾಷೆ", "Close": "ಮುಚ್ಚಿ"
    }
  };

  const GUIDE = {
    en: { title: "How to swap a shift", steps: [
      "<b>Employee A</b>: sign in as Employee, open <b>My Portal</b> and click <b>⇄ Swap</b> next to the shift you cannot work (or <b>Ask a colleague to swap</b>).",
      "Pick a colleague from the list. Only people who are <b>eligible</b> (free, skilled, rested) are shown, and same-role people appear first. Add a note and choose In-app or Email.",
      "Click <b>Send request to colleague</b>. The stage shows <b>⏳ Waiting for colleague</b>.",
      "<b>Employee B</b>: sign in, an amber card <b>Swap requests waiting for your answer</b> appears. Click <b>✔ Accept</b> or <b>✕ Decline</b>.",
      "If B accepts, the stage becomes <b>✅ agreed · awaiting manager</b>. If B declines, A can ask someone else.",
      "<b>Manager</b>: open <b>Shift Swaps</b> and click <b>Approve</b> or <b>Reject</b>. The rules engine re-checks everything before the roster changes.",
      "Both employees get a notification with the result."] },
    hi: { title: "शिफ्ट की अदला-बदली कैसे करें", steps: [
      "<b>कर्मचारी A</b>: कर्मचारी के रूप में साइन इन करें, <b>मेरा पोर्टल</b> खोलें और जिस शिफ्ट पर काम नहीं कर सकते उसके आगे <b>⇄ Swap</b> दबाएं।",
      "सूची से सहकर्मी चुनें। केवल <b>योग्य</b> लोग (खाली, कुशल, आराम किए हुए) दिखते हैं; समान भूमिका वाले पहले दिखते हैं। नोट लिखें और In-app या Email चुनें।",
      "<b>Send request to colleague</b> दबाएं। स्थिति <b>⏳ सहकर्मी की प्रतीक्षा</b> दिखेगी।",
      "<b>कर्मचारी B</b>: साइन इन करें, पीला कार्ड <b>आपके उत्तर की प्रतीक्षा में अनुरोध</b> दिखेगा। <b>✔ Accept</b> या <b>✕ Decline</b> दबाएं।",
      "B स्वीकार करे तो स्थिति <b>✅ सहमत · प्रबंधक की मंज़ूरी बाकी</b> हो जाती है। B मना करे तो A किसी और से पूछ सकता है।",
      "<b>प्रबंधक</b>: <b>Shift Swaps</b> खोलें और <b>Approve</b> या <b>Reject</b> दबाएं। रोस्टर बदलने से पहले नियम इंजन सब दोबारा जाँचता है।",
      "दोनों कर्मचारियों को परिणाम की सूचना मिलती है।"] },
    kn: { title: "ಶಿಫ್ಟ್ ಬದಲಾವಣೆ ಹೇಗೆ ಮಾಡುವುದು", steps: [
      "<b>ಉದ್ಯೋಗಿ A</b>: ಉದ್ಯೋಗಿಯಾಗಿ ಸೈನ್ ಇನ್ ಮಾಡಿ, <b>ನನ್ನ ಪೋರ್ಟಲ್</b> ತೆರೆದು ಕೆಲಸ ಮಾಡಲಾಗದ ಶಿಫ್ಟ್ ಪಕ್ಕದ <b>⇄ Swap</b> ಒತ್ತಿ.",
      "ಪಟ್ಟಿಯಿಂದ ಸಹೋದ್ಯೋಗಿಯನ್ನು ಆರಿಸಿ. <b>ಅರ್ಹ</b> ಜನರು (ಖಾಲಿ, ಕೌಶಲ್ಯವುಳ್ಳ, ವಿಶ್ರಾಂತಿ ಪಡೆದ) ಮಾತ್ರ ಕಾಣಿಸುತ್ತಾರೆ; ಅದೇ ಪಾತ್ರದವರು ಮೊದಲು. ಟಿಪ್ಪಣಿ ಬರೆದು In-app ಅಥವಾ Email ಆರಿಸಿ.",
      "<b>Send request to colleague</b> ಒತ್ತಿ. ಸ್ಥಿತಿ <b>⏳ ಸಹೋದ್ಯೋಗಿಗೆ ಕಾಯುತ್ತಿದೆ</b> ಎಂದು ತೋರಿಸುತ್ತದೆ.",
      "<b>ಉದ್ಯೋಗಿ B</b>: ಸೈನ್ ಇನ್ ಮಾಡಿ, ಹಳದಿ ಕಾರ್ಡ್ <b>ನಿಮ್ಮ ಉತ್ತರಕ್ಕೆ ಕಾಯುತ್ತಿರುವ ಮನವಿಗಳು</b> ಕಾಣುತ್ತದೆ. <b>✔ Accept</b> ಅಥವಾ <b>✕ Decline</b> ಒತ್ತಿ.",
      "B ಒಪ್ಪಿದರೆ ಸ್ಥಿತಿ <b>✅ ಒಪ್ಪಿಗೆ · ಮ್ಯಾನೇಜರ್ ಅನುಮೋದನೆ ಬಾಕಿ</b> ಆಗುತ್ತದೆ. B ನಿರಾಕರಿಸಿದರೆ A ಬೇರೆಯವರನ್ನು ಕೇಳಬಹುದು.",
      "<b>ಮ್ಯಾನೇಜರ್</b>: <b>Shift Swaps</b> ತೆರೆದು <b>Approve</b> ಅಥವಾ <b>Reject</b> ಒತ್ತಿ. ರೋಸ್ಟರ್ ಬದಲಾಗುವ ಮೊದಲು ನಿಯಮ ಎಂಜಿನ್ ಎಲ್ಲವನ್ನೂ ಮರುಪರಿಶೀಲಿಸುತ್ತದೆ.",
      "ಇಬ್ಬರು ಉದ್ಯೋಗಿಗಳಿಗೂ ಫಲಿತಾಂಶದ ಅಧಿಸೂಚನೆ ಹೋಗುತ್ತದೆ."] }
  };

  let lang = localStorage.getItem('sw_lang') || 'en';
  const orig = new WeakMap(), origPh = new WeakMap();

  function tr(s) {
    const t = s.trim();
    if (!t) return s;
    const m = t.match(/^([^A-Za-z0-9\u0900-\u0DFF]*)(.*?)([^A-Za-z0-9\u0900-\u0DFF]*)$/);
    const dict = T[lang] || {};
    const hit = dict[m[2]] || dict[t];
    return hit ? s.replace(t, (dict[t] ? hit : m[1] + hit + m[3])) : s;
  }

  function apply() {
    document.documentElement.lang = lang;
    const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, {
      acceptNode: n => /SCRIPT|STYLE/.test(n.parentNode.nodeName) || !n.nodeValue.trim() ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT });
    const nodes = []; while (w.nextNode()) nodes.push(w.currentNode);
    nodes.forEach(n => {
      if (!orig.has(n)) orig.set(n, n.nodeValue);
      n.nodeValue = lang === 'en' ? orig.get(n) : tr(orig.get(n));
    });
    document.querySelectorAll('[placeholder]').forEach(el => {
      if (!origPh.has(el)) origPh.set(el, el.placeholder);
      el.placeholder = lang === 'en' ? origPh.get(el) : tr(origPh.get(el));
    });
  }

  /* ---------- guide modal ---------- */
  const guide = document.createElement('div'); guide.id = 'sw-guide';
  document.body.appendChild(guide);
  function openGuide() {
    const g = GUIDE[lang] || GUIDE.en;
    guide.innerHTML = `<div class="box"><button class="x2" id="sw-gx">✕</button><h3>🔄 ${g.title}</h3><ol>${g.steps.map(s => `<li>${s}</li>`).join('')}</ol></div>`;
    guide.classList.add('open');
    document.getElementById('sw-gx').onclick = () => guide.classList.remove('open');
  }
  guide.addEventListener('click', e => { if (e.target === guide) guide.classList.remove('open'); });

  /* ---------- dock ---------- */
  const dock = document.createElement('div'); dock.id = 'sw-dock';
  dock.innerHTML = `<select id="sw-lang" title="Language">
      <option value="en">English</option><option value="hi">हिन्दी</option><option value="kn">ಕನ್ನಡ</option></select>
    <button id="sw-help">❓ Swap Guide</button>`;
  document.body.appendChild(dock);
  const sel = document.getElementById('sw-lang'); sel.value = lang;
  sel.onchange = () => { lang = sel.value; localStorage.setItem('sw_lang', lang); apply(); };
  document.getElementById('sw-help').onclick = openGuide;

  /* ---------- emergency ---------- */
  fetch('/api/status').then(r => r.ok ? r.json() : null).then(s => {
    if (!s) return;
    if (s.emergency) {
      const b = document.createElement('div'); b.id = 'sw-banner';
      b.textContent = '🚨 EMERGENCY MODE ACTIVE: rules relaxed (8h rest · 16h/day · 7 days), reserve staff prioritised';
      document.body.prepend(b);
    }
    if (s.role === 'manager') {
      const btn = document.createElement('button');
      btn.className = 'em' + (s.emergency ? ' on' : '');
      btn.textContent = s.emergency ? '✅ Emergency OFF' : '🚨 EMERGENCY';
      btn.onclick = () => {
        if (!s.emergency && !confirm('Activate EMERGENCY MODE? Rules will be relaxed and reserve staff alerted.')) return;
        fetch(s.emergency ? '/emergency/off' : '/emergency/on', { method: 'POST' }).then(() => location.reload());
      };
      dock.appendChild(btn);
    }
    apply();
  }).catch(apply);

  apply();
})();
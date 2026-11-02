/** Research ethics copy — replace after ethics review if needed. */

export const RESEARCH_ETHICS = {
  ja: {
    consentLabel: '研究への協力・データ取得について同意します',
    detailLink: '詳細を見る',
    modalTitle: '研究倫理に関する説明',
    close: '閉じる',
    sections: [
      {
        heading: '研究の目的',
        body:
          '本シミュレーションは、気候変動下の流域適応政策に関する理解と意思決定過程を明らかにするための研究・教育活動の一環として実施されます。収集した操作ログと結果は、学術研究・教材改善・ワークショップ評価に利用されることがあります。',
      },
      {
        heading: '取得するデータの種類',
        body:
          '取得対象は、表示名（ユーザ名／チーム名）、選択した気候シナリオとモード、政策スライダーの操作、画面遷移、分析操作、イベント確認、最終スコア等の操作ログおよび結果要約です。カメラ映像そのものや生体情報は取得しません。',
      },
      {
        heading: 'データの取り扱い・保管・匿名化',
        body:
          'データは研究目的の範囲で保管・分析されます。公表時は個人が特定されにくい形で集計・記述します。操作ログはセッション終了時にサーバへ自動保存されます。',
      },
      {
        heading: '参加の任意性・同意撤回',
        body:
          '参加は任意です。同意しない場合はシミュレーションを開始できません。開始後に参加をやめたい場合は、その旨を実施者に伝えてください。可能な範囲で以降のデータ利用を停止します。',
      },
      {
        heading: '想定される不利益・利益',
        body:
          '本活動による身体的リスクはありません。画面操作に伴う軽い疲労の可能性はあります。利益として、流域適応政策のトレードオフを体験的に学べることが期待されます。',
      },
      {
        heading: '問い合わせ先',
        body:
          '本研究・ワークショップに関する問い合わせは、実施責任者（ワークショップ主催者）までご連絡ください。連絡先は当日配布資料または案内スライドに記載します。',
      },
    ],
  },
  en: {
    consentLabel: 'I consent to the collection of data for this research',
    detailLink: 'View details',
    modalTitle: 'Research Participation and Data Use',
    close: 'Close',
    sections: [
      {
        heading: 'Purpose',
        body:
          'This simulation is part of a research and educational initiative examining how people understand and make decisions about climate adaptation in river basins. Activity logs and simulation results may be used for academic research, educational improvements, and workshop evaluation.',
      },
      {
        heading: 'Data collected',
        body:
          'We collect display names (user or team name), the selected climate scenario and mode, policy slider adjustments, screen navigation, analysis interactions, event confirmations, activity logs, and result summaries. We do not collect camera footage or biometric data.',
      },
      {
        heading: 'Handling, storage, and anonymization',
        body:
          'The data will be stored and analyzed for research purposes. Any published findings will be aggregated or de-identified to reduce the likelihood that individuals can be identified. Activity logs are saved automatically to the server at the end of the session.',
      },
      {
        heading: 'Voluntary participation and withdrawal',
        body:
          'Participation is voluntary. You cannot begin the simulation without providing consent. If you wish to withdraw after starting, please inform the facilitator. We will stop using your data from that point onward wherever practicable.',
      },
      {
        heading: 'Risks and benefits',
        body:
          'This activity involves no anticipated physical risks, although using the screen may cause mild fatigue. A potential benefit is gaining a practical understanding of the trade-offs involved in river basin adaptation policies.',
      },
      {
        heading: 'Contact',
        body:
          'If you have any questions about this research or workshop, please contact the organizer listed in the handout or introductory slides.',
      },
    ],
  },
}

export function getResearchEthics(lang = 'ja') {
  return RESEARCH_ETHICS[lang] || RESEARCH_ETHICS.ja
}

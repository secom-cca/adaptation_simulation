// csvから読み込む変数
var result1 = [];
var result0 = [];
var result2 = [];
var your_data = [];

// 共通変数
var yourname = "";
var scenarioname = "";
var policyname = ["植林・森林保全", "住宅移転・嵩上げ", "ダム・堤防工事", "田んぼダム工事", "防災訓練・啓発", "交通網の充実", "農業研究開発"];
var scorename = ["農作物収量", "洪水被害", "自治体予算", "生態系", "都市利便性"]
// 合計スコア
var sum2050 = 0;
var sum2075 = 0;
var sum2100 = 0;

var bunyabalancescore = [];
var sedaibalancescore = 0;


var yourscore = [];
var allscore = [];


// 获取后端URL的函数 - 使用统一配置
function getBackendUrl() {
    // 优先使用全局配置
    if (window.APP_CONFIG) {
        return window.APP_CONFIG.getBackendUrl();
    }

    // 降级方案：检测当前环境
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        return 'http://localhost:8000';
    } else {
        return 'https://web-production-5fb04.up.railway.app';
    }
}

// 显示错误信息的函数
function showErrorMessage(message) {
    const errorDiv = document.createElement('div');
    errorDiv.style.cssText = 'color: red; font-size: 18px; text-align: center; margin: 20px; padding: 10px; border: 1px solid red; background-color: #ffe6e6;';
    errorDiv.textContent = message;
    document.body.insertBefore(errorDiv, document.body.firstChild);
}

//统一的用户数据获取函数
function get_nameCSV(){
    const userName = localStorage.getItem('userName') || 'default_user';
    const backendUrl = getBackendUrl();

    console.log(`🔍 正在获取用户数据: ${userName} from ${backendUrl}`);

    var req = new XMLHttpRequest();
    req.open("get", `${backendUrl}/api/user_data/${userName}`, true);
    req.send(null);

    req.onload = function(){
        if (req.status === 200) {
            try {
                const userData = JSON.parse(req.responseText);
                console.log('✅ 用户数据获取成功:', userData);

                // 检查数据完整性
                if (!userData.data_complete) {
                    console.warn(`⚠️ 数据不完整: 只有 ${userData.periods_found} 个时期的数据`);
                    showErrorMessage(`データが不完全です。${userData.periods_found}期間のデータのみ見つかりました。`);
                }

                // 直接处理所有数据，避免多次API调用
                processAllUserData(userData);

            } catch (e) {
                console.error('❌ 用户数据解析失败:', e);
                showErrorMessage('データの解析に失敗しました');
            }
        } else {
            console.error('❌ 用户数据加载失败:', req.status);
            showErrorMessage('ユーザーデータの読み込みに失敗しました');
        }
    }

    req.onerror = function() {
        console.error('❌ 网络请求失败');
        showErrorMessage('ネットワークエラーが発生しました');
    }
}

// 统一处理所有用户数据的函数
function processAllUserData(userData) {
    try {
        // 处理用户名数据
        if (userData.your_name_csv) {
            convert_nameCSVtoArray(userData.your_name_csv);
        }

        // 处理评分数据
        if (userData.block_scores_tsv) {
            convert_dataCSVtoArray(userData.block_scores_tsv);
        }

        console.log('✅ 所有数据处理完成');
    } catch (e) {
        console.error('❌ 数据处理失败:', e);
        showErrorMessage('データの処理に失敗しました');
    }
}

// 保留原有函数作为备用（现在不会被调用）
function get_dataCSV(){
    console.log('⚠️ get_dataCSV 被调用，但数据已在 get_nameCSV 中处理');
}
// 1つ目のCSVを配列に変換
function convert_nameCSVtoArray(str){
    result1 = [];
    var tmp = str.split("\n");
    for(var i=0;i<tmp.length;++i){
        result1[i] = [tmp[i].trim()]; // 1列しかないので配列に
    }
    console.log('✅ 用户名数据处理完成:', result1);
    // 不再调用 get_dataCSV()，数据已在 processAllUserData 中统一处理
}
// 3つ目のCSVを配列に変換し、1つ目の値を使って処理
function convert_dataCSVtoArray(str){
    console.log('开始处理评分数据...');
    console.log('评分数据前500字符:', str.substring(0, 500));
    result2 = [];
    var tmp = str.split("\n");
    console.log('数据行数:', tmp.length);
    for(var i=0;i<tmp.length;++i){
        result2[i] = tmp[i].split('\t');
    }

    // プレイヤー名を取得
    yourname = result1[1][0].trim();
    console.log('当前玩家名:', yourname);

    document.getElementById("yourname").innerText=yourname;

    document.getElementById("bunya0").innerText=scorename[0];
    document.getElementById("bunya1").innerText=scorename[1];
    document.getElementById("bunya2").innerText=scorename[2];
    document.getElementById("bunya3").innerText=scorename[3];
    document.getElementById("bunya4").innerText=scorename[4];

    console.log('开始查找玩家数据...');
    for(var i=1;i<tmp.length;++i){
        if (result2[i][0] == yourname){
            console.log('找到玩家数据，行', i, ':', result2[i]);
            your_data.push(result2[i]);
        }
    }
    console.log('玩家数据总数:', your_data.length);

    // 2050年
    var jsonStr2050score = your_data[0][4].replace(/'/g, '"').replace(/np\.float64\(/g, '').replace(/\)/g, ''); // numpy型を除去
    var obj2050score = JSON.parse(jsonStr2050score);
    sum2050 = Object.values(obj2050score).reduce(function(acc, val){
    return acc + Number(val);
    }, 0);
    // 2075年
    var jsonStr2075score = your_data[1][4].replace(/'/g, '"').replace(/np\.float64\(/g, '').replace(/\)/g, ''); // numpy型を除去
    var obj2075score = JSON.parse(jsonStr2075score);
    sum2075 = Object.values(obj2075score).reduce(function(acc, val){
    return acc + Number(val);
    }, 0);
    // 2100年
    var jsonStr2100score = your_data[2][4].replace(/'/g, '"').replace(/np\.float64\(/g, '').replace(/\)/g, ''); // numpy型を除去
    var obj2100score = JSON.parse(jsonStr2100score);
    sum2100 = Object.values(obj2100score).reduce(function(acc, val){
    return acc + Number(val);
    }, 0);


    // バランススコアの計算
    bunyabalancescore = [
    Number(your_data[0][5]),
    Number(your_data[1][5]),
    Number(your_data[2][5])
    ];

    const variance = arr => {
    const avr = arr.reduce((a,b) => a+b)/arr.length;
    return arr.reduce((a,c) => (a + ((c - avr) ** 2)),0)/arr.length;
    };
    sedaibalancescore = variance(bunyabalancescore)

    // 名前、分野毎のスコア、合計スコア、分野間バランススコア、世代間バランススコアを格納
    yourscore = [
        yourname,
        Number(obj2050score["収量"]) + Number(obj2075score["収量"]) + Number(obj2100score["収量"]),
        Number(obj2050score["洪水被害"]) + Number(obj2075score["洪水被害"]) + Number(obj2100score["洪水被害"]),
        Number(obj2050score["予算"]) + Number(obj2075score["予算"]) + Number(obj2100score["予算"]),
        Number(obj2050score["生態系"]) + Number(obj2075score["生態系"]) + Number(obj2100score["生態系"]),
        Number(obj2050score["都市利便性"]) + Number(obj2075score["都市利便性"]) + Number(obj2100score["都市利便性"]),
        sum2050 + sum2075 + sum2100,
        bunyabalancescore[0] + bunyabalancescore[1] + bunyabalancescore[2],
        sedaibalancescore
    ];

    // プレイヤー全員の結果をresult2より取得
    // プレイヤー全員の結果をresult2より取得
    allscore = []; // ここで初期化
    for(var i=1;i<result2.length; i=i+3){ // 1行目はヘッダーなのでi=1から
        // 更严格的数据检查
        if (!result2[i] || !result2[i+1] || !result2[i+2] ||
            !result2[i][4] || !result2[i+1][4] || !result2[i+2][4] ||
            result2[i].length < 6 || result2[i+1].length < 6 || result2[i+2].length < 6) {
            console.log('跳过不完整的数据行:', i);
            continue;
        }
        var playername = result2[i][0];
        console.log('处理玩家:', playername);

        try {
            var obj2050score = JSON.parse(result2[i][4].replace(/'/g, '"').replace(/np\.float64\(/g, '').replace(/\)/g, ''));
            var obj2075score = JSON.parse(result2[i+1][4].replace(/'/g, '"').replace(/np\.float64\(/g, '').replace(/\)/g, ''));
            var obj2100score = JSON.parse(result2[i+2][4].replace(/'/g, '"').replace(/np\.float64\(/g, '').replace(/\)/g, ''));
        } catch (error) {
            console.error('JSON解析错误，玩家:', playername, '错误:', error);
            continue;
        }

        var sum2050 = Object.values(obj2050score).reduce((acc, val) => acc + Number(val), 0);
        var sum2075 = Object.values(obj2075score).reduce((acc, val) => acc + Number(val), 0);
        var sum2100 = Object.values(obj2100score).reduce((acc, val) => acc + Number(val), 0);

        var bunyabalancescore_player = [
            Number(result2[i][5]),
            Number(result2[i+1][5]),
            Number(result2[i+2][5])
        ];
        var sedaibalancescore_player = variance(bunyabalancescore_player);
        var playerscore = [
            playername,
            Number(obj2050score["収量"]) + Number(obj2075score["収量"]) + Number(obj2100score["収量"]),
            Number(obj2050score["洪水被害"]) + Number(obj2075score["洪水被害"]) + Number(obj2100score["洪水被害"]),
            Number(obj2050score["予算"]) + Number(obj2075score["予算"]) + Number(obj2100score["予算"]),
            Number(obj2050score["生態系"]) + Number(obj2075score["生態系"]) + Number(obj2100score["生態系"]),
            Number(obj2050score["都市利便性"]) + Number(obj2075score["都市利便性"]) + Number(obj2100score["都市利便性"]),
            sum2050 + sum2075 + sum2100,
            bunyabalancescore_player[0] + bunyabalancescore_player[1] + bunyabalancescore_player[2],
            sedaibalancescore_player
        ];
        allscore.push(playerscore);
    }


    // 分野名とallscoreのインデックス対応
    const fieldIndex = {
        "収量": 1,
        "洪水被害": 2,
        "予算": 3,
        "生態系": 4,
        "都市利便性": 5,
        "総合": 6,
        "分野間バランス": 7,
        "世代間バランス": 8
    };

    // 分野ごとにTOP3を取得して表示
    function showTop3AndRank() {
        const fields = ["収量", "洪水被害", "予算", "生態系", "都市利便性", "総合", "分野間バランス", "世代間バランス"];
        fields.forEach(field => {
            // 降順ソート（大きい順）でランキング配列を作成
            const sorted = allscore
                .slice()
                .sort((a, b) => b[fieldIndex[field]] - a[fieldIndex[field]]);

            // TOP3を抽出
            const top3 = sorted.slice(0, 3);

            // yournameの順位を取得
            let yourRank = sorted.findIndex(row => row[0] === yourscore[0]) + 1; // 1位始まり
            let yourScore = yourscore[fieldIndex[field]];

            // 1位、2位、3位の名前とスコアをそれぞれ別IDで出力
            const nameElem1 = document.getElementById(`name1_${field}`);
            const scoreElem1 = document.getElementById(`score1_${field}`);
            const nameElem2 = document.getElementById(`name2_${field}`);
            const scoreElem2 = document.getElementById(`score2_${field}`);
            const nameElem3 = document.getElementById(`name3_${field}`);
            const scoreElem3 = document.getElementById(`score3_${field}`);
            const yourRankElem = document.getElementById(`yourrank_${field}`);
            const yourNameElem = document.getElementById(`yourname_${field}`);
            const yourScoreElem = document.getElementById(`yourscore_${field}`);

            if (nameElem1 && top3[0]) nameElem1.innerText = top3[0][0];
            if (scoreElem1 && top3[0]) scoreElem1.innerText = top3[0][fieldIndex[field]].toFixed(1);
            if (nameElem2 && top3[1]) nameElem2.innerText = top3[1][0];
            if (scoreElem2 && top3[1]) scoreElem2.innerText = top3[1][fieldIndex[field]].toFixed(1);
            if (nameElem3 && top3[2]) nameElem3.innerText = top3[2][0];
            if (scoreElem3 && top3[2]) scoreElem3.innerText = top3[2][fieldIndex[field]].toFixed(1);
            if (yourRankElem) yourRankElem.innerText = yourRank;
            if (yourNameElem) yourNameElem.innerText = yourname;
            if (yourScoreElem) yourScoreElem.innerText = yourScore.toFixed(1);;
        });
    }

    // 各分野のTOP3とあなたの順位を表示
    showTop3AndRank();

}

get_nameCSV();







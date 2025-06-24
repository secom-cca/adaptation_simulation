
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
// スコア(0~100点)
var score2050 = [];
var score2075 = [];
var score2100 = [];
var scoretotal = [];
var bunyabalancescore = [];
var sedaibalancescore = [];
var bunyabalancetotal = 0;

// 講評用
var bunyabalancecomment = ["良好！快適な生活が送れますね。", "まあまあ。生活には少し不安が残ります。", "良くない……。住民からの反発も強いかも。"]
var sedaibalancecomment = ["いい感じ！持続可能な環境が作れています。", "まずまず。住みやすい環境は作り続けていくことが重要です。", "ぐちゃぐちゃ……。持続可能な環境作りは大切です！"]




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

        // 处理决策日志数据
        if (userData.decision_log_csv) {
            convert_logCSVtoArray(userData.decision_log_csv);
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
function get_logCSV(){
    console.log('⚠️ get_logCSV 被调用，但数据已在 get_nameCSV 中处理');
}

function get_dataCSV(){
    console.log('⚠️ get_dataCSV 被调用，但数据已在 get_nameCSV 中处理');
}




// 1つ目のCSVを配列に変換
function convert_nameCSVtoArray(str){
    result1 = [];
    var tmp = str.split("\n");
    for(var i=0;i<tmp.length;++i){
        result1[i] = tmp[i].split('\t');
    }
    console.log('✅ 用户名数据处理完成:', result1);
    // 不再调用 get_logCSV()，数据已在 processAllUserData 中统一处理
}

// 2つ目のCSVを配列に変換
function convert_logCSVtoArray(str){
    result0 = [];
    var tmp = str.split("\n");
    for(var i=0;i<tmp.length;++i){
        result0[i] = tmp[i].split(',');
    }
    console.log('✅ 决策日志数据处理完成:', result0.length, '条记录');
    // 不再调用 get_dataCSV()，数据已在 processAllUserData 中统一处理
}
// 3つ目のCSVを配列に変換し、1つ目の値を使って処理
function convert_dataCSVtoArray(str){
    result2 = [];
    var tmp = str.split("\n");
    for(var i=0;i<tmp.length;++i){
        result2[i] = tmp[i].split('\t');
    }

    var yourname = result1[1][0].trim();

    for(var i=0;i<tmp.length;++i){
        if (result2[i][0] == yourname){
            your_data.push(result2[i]);
        }
    }

    // 結果を表示
    document.getElementById("yourname").innerText=your_data[0][0];



    // 2050年
    var jsonStr2050score = your_data[0][4].replace(/'/g, '"'); // シングルクォートをダブルクォートに変換
    var obj2050score = JSON.parse(jsonStr2050score);
    score2050 = [
    Number(obj2050score["収量"]),
    Number(obj2050score["洪水被害"]),
    Number(obj2050score["予算"]),
    Number(obj2050score["生態系"]),
    Number(obj2050score["都市利便性"])
    ];
    // 2075年
    var jsonStr2075score = your_data[1][4].replace(/'/g, '"'); // シングルクォートをダブルクォートに変換
    var obj2075score = JSON.parse(jsonStr2075score);
    score2075 = [
    Number(obj2075score["収量"]),
    Number(obj2075score["洪水被害"]),
    Number(obj2075score["予算"]),
    Number(obj2075score["生態系"]),
    Number(obj2075score["都市利便性"])
    ];
    // 2100年
    var jsonStr2100score = your_data[2][4].replace(/'/g, '"'); // シングルクォートをダブルクォートに変換
    var obj2100score = JSON.parse(jsonStr2100score);
    score2100 = [
    Number(obj2100score["収量"]),
    Number(obj2100score["洪水被害"]),
    Number(obj2100score["予算"]),
    Number(obj2100score["生態系"]),
    Number(obj2100score["都市利便性"])
    ];
    scoretotal = [
    score2050[0] + score2075[0] + score2100[0],
    score2050[1] + score2075[1] + score2100[1],
    score2050[2] + score2075[2] + score2100[2],
    score2050[3] + score2075[3] + score2100[3],
    score2050[4] + score2075[4] + score2100[4]
    ];
    // スコアの最大値と最小値を取得
    let minscore = scoretotal[0];
    let minscorename = scorename[0];
    let maxscore = scoretotal[0];
    let maxscorename = scorename[0];
    for (var i = 0; i < 5; i++) {
        if (minscore > scoretotal[i]){
            minscore = scoretotal[i];
            minscorename = scorename[i];
        }
        if (maxscore < scoretotal[i]){
            maxscore = scoretotal[i];
            maxscorename = scorename[i];
        }
    }
    document.getElementById("maxscorename").innerText=maxscorename;
    document.getElementById("minscorename").innerText=minscorename;


    // バランススコアの計算
    bunyabalancescore = [
    Number(your_data[0][5]),
    Number(your_data[1][5]),
    Number(your_data[2][5])
    ];
    bunyabalancetotal = bunyabalancescore[0] + bunyabalancescore[1] + bunyabalancescore[2];

    let bunyaidx = 0;
    if (bunyabalancetotal >= 150){
    bunyaidx = 0;
    }else if (bunyabalancetotal < 150 && bunyabalancetotal >= 100){
    bunyaidx = 1;
    }else{
    bunyaidx = 2;
    }
    
    document.getElementById("bunyabalance").innerText=bunyabalancecomment[bunyaidx];

    const variance = arr => {
    const avr = arr.reduce((a,b) => a+b)/arr.length;
    return arr.reduce((a,c) => (a + ((c - avr) ** 2)),0)/arr.length;
    };

    sedaibalancescore = variance(bunyabalancescore);
    let sedaiidx = 0;
    if (sedaibalancescore >= 30){
        sedaiidx = 0;
    }else if (sedaibalancescore < 30 && sedaibalancescore >= 10){
        sedaiidx = 1;
    }else{
        sedaiidx = 2;
    }


    document.getElementById("sedaibalance").innerText=sedaibalancecomment[sedaiidx];


    // 施策名
    var choice2050 = result0[result0.length-52].slice(1, 8).map(Number);
    var choice2075 = result0[result0.length-27].slice(1, 8).map(Number);
    var choice2100 = result0[result0.length- 2].slice(1, 8).map(Number);
    choice2050[0] /= 20;
    choice2075[0] /= 20;
    choice2100[0] /= 20;
    choice2050[2] *= 5;
    choice2075[2] *= 5;
    choice2100[2] *= 5;
    // スコアの最大値と最小値を取得
    let maxpolicy = (choice2050[0] + choice2075[0] + choice2100[0]);
    let maxpolicyname = policyname[0];
    for (var i = 0; i < choice2050.length; i++) {
        if (maxpolicy < (choice2050[i] + choice2075[i] + choice2100[i])){
            maxpolicy = (choice2050[i] + choice2075[i] + choice2100[i])
            maxpolicyname = policyname[i];
        }
    }

    document.getElementById("bestpolicy").innerText=maxpolicyname;



}

get_nameCSV();
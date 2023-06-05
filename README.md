# pygit
## X2-1
gitのサブセットをpythonで記述しました。行ったのは、addとcommitそれぞれの部分的実装です。バイナリの操作が中心でした。実行方法は次のようになります。

*add*
```
python path/mygit.py add files
```
*commit*
```
python path/mygit.py commit -m msg
```
### 制約
- `config`から`user`と`email`を読むので、事前に`--local`で作っておく。
- コマンドはプロジェクトのルート直下のファイルのみ対応し、ディレクトリは非対応。
- `HEAD`はデフォルトの`main`を仮定し、変更はしないものとする。`checkout`は未実装。

### 参考サイト
* [Gitを作ってみる（理解編）](https://qiita.com/noshishi/items/60a6fe7c63097950911b)
* [Gitを作ってみる（開発編）](https://qiita.com/noshishi/items/823bc46d971ac1fe8215)
* [Write yourself a Git!](https://wyag.thb.lt/)

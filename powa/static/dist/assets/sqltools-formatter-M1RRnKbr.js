import{c as s,g as G}from"./lodash-CmFMvF3r.js";var l={},p={},a={},_={},D={};(function(A){A.__esModule=!0;var N=/[\\^$.*+?()[\]{}|]/g,o=RegExp(N.source);function O(i){return i&&o.test(i)?i.replace(N,"\\$&"):i||""}A.default=O})(D);var C={};(function(A){A.__esModule=!0,A.TokenTypes=void 0,function(N){N.WHITESPACE="whitespace",N.WORD="word",N.STRING="string",N.RESERVED="reserved",N.RESERVED_TOP_LEVEL="reserved-top-level",N.RESERVED_TOP_LEVEL_NO_INDENT="reserved-top-level-no-indent",N.RESERVED_NEWLINE="reserved-newline",N.OPERATOR="operator",N.NO_SPACE_OPERATOR="no-space-operator",N.OPEN_PAREN="open-paren",N.CLOSE_PAREN="close-paren",N.LINE_COMMENT="line-comment",N.BLOCK_COMMENT="block-comment",N.NUMBER="number",N.PLACEHOLDER="placeholder",N.SERVERVARIABLE="servervariable"}(A.TokenTypes||(A.TokenTypes={}))})(C);(function(A){var N=s&&s.__importDefault||function(R){return R&&R.__esModule?R:{default:R}};A.__esModule=!0;var o=N(D),O=C,i=function(){function R(e){this.WHITESPACE_REGEX=/^(\s+)/u,this.NUMBER_REGEX=/^((-\s*)?[0-9]+(\.[0-9]+)?|0x[0-9a-fA-F]+|0b[01]+|([a-fA-F0-9]{8}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{4}-[a-fA-F0-9]{12}))\b/u,this.AMBIGUOS_OPERATOR_REGEX=/^(\?\||\?&)/u,this.OPERATOR_REGEX=/^(!=|<>|>>|<<|==|<=|>=|!<|!>|\|\|\/|\|\/|\|\||~~\*|~~|!~~\*|!~~|~\*|!~\*|!~|:=|=>|&&|@>|<@|#-|@@|@|.)/u,this.NO_SPACE_OPERATOR_REGEX=/^(::|->>|->|#>>|#>)/u,this.BLOCK_COMMENT_REGEX=/^(\/\*[^]*?(?:\*\/|$))/u,this.LINE_COMMENT_REGEX=this.createLineCommentRegex(e.lineCommentTypes),this.RESERVED_TOP_LEVEL_REGEX=this.createReservedWordRegex(e.reservedTopLevelWords),this.RESERVED_TOP_LEVEL_NO_INDENT_REGEX=this.createReservedWordRegex(e.reservedTopLevelWordsNoIndent),this.RESERVED_NEWLINE_REGEX=this.createReservedWordRegex(e.reservedNewlineWords),this.RESERVED_PLAIN_REGEX=this.createReservedWordRegex(e.reservedWords),this.WORD_REGEX=this.createWordRegex(e.specialWordChars),this.STRING_REGEX=this.createStringRegex(e.stringTypes),this.OPEN_PAREN_REGEX=this.createParenRegex(e.openParens),this.CLOSE_PAREN_REGEX=this.createParenRegex(e.closeParens),this.INDEXED_PLACEHOLDER_REGEX=this.createPlaceholderRegex(e.indexedPlaceholderTypes,"[0-9]*"),this.IDENT_NAMED_PLACEHOLDER_REGEX=this.createPlaceholderRegex(e.namedPlaceholderTypes,"[a-zA-Z0-9._$]+"),this.STRING_NAMED_PLACEHOLDER_REGEX=this.createPlaceholderRegex(e.namedPlaceholderTypes,this.createStringPattern(e.stringTypes))}return R.prototype.createLineCommentRegex=function(e){var n="((?<!#)>|(?:[^>]))";return new RegExp("^((?:".concat(e.map(function(I){return(0,o.default)(I)}).join("|"),")").concat(n,`.*?(?:\r
|\r|
|$))`),"u")},R.prototype.createReservedWordRegex=function(e){var n=e.join("|").replace(/ /gu,"\\s+");return new RegExp("^(".concat(n,")\\b"),"iu")},R.prototype.createWordRegex=function(e){return new RegExp("^([\\p{Alphabetic}\\p{Mark}\\p{Decimal_Number}\\p{Connector_Punctuation}\\p{Join_Control}".concat(e.join(""),"]+)"),"u")},R.prototype.createStringRegex=function(e){return new RegExp("^("+this.createStringPattern(e)+")","u")},R.prototype.createStringPattern=function(e){var n={"``":"((`[^`]*($|`))+)","[]":"((\\[[^\\]]*($|\\]))(\\][^\\]]*($|\\]))*)",'""':'(("[^"\\\\]*(?:\\\\.[^"\\\\]*)*("|$))+)',"''":"(('[^'\\\\]*(?:\\\\.[^'\\\\]*)*('|$))+)","N''":"((N'[^N'\\\\]*(?:\\\\.[^N'\\\\]*)*('|$))+)","E''":"(((E|e)'[^'\\\\]*(?:\\\\.[^'\\\\]*)*('|$))+)"};return e.map(function(I){return n[I]}).join("|")},R.prototype.createParenRegex=function(e){var n=this;return new RegExp("^("+e.map(function(I){return n.escapeParen(I)}).join("|")+")","iu")},R.prototype.escapeParen=function(e){return e.length===1?(0,o.default)(e):"\\b"+e+"\\b"},R.prototype.createPlaceholderRegex=function(e,n){if(!e||e.length===0)return null;var I=e.map(o.default).join("|");return new RegExp("^((?:".concat(I,")(?:").concat(n,"))"),"u")},R.prototype.tokenize=function(e){if(!e)return[];for(var n=[],I;e.length;)I=this.getNextToken(e,I),e=e.substring(I.value.length),n.push(I);return n},R.prototype.getNextToken=function(e,n){return this.getWhitespaceToken(e)||this.getCommentToken(e)||this.getStringToken(e)||this.getOpenParenToken(e)||this.getCloseParenToken(e)||this.getAmbiguosOperatorToken(e)||this.getNoSpaceOperatorToken(e)||this.getServerVariableToken(e)||this.getPlaceholderToken(e)||this.getNumberToken(e)||this.getReservedWordToken(e,n)||this.getWordToken(e)||this.getOperatorToken(e)},R.prototype.getWhitespaceToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.WHITESPACE,regex:this.WHITESPACE_REGEX})},R.prototype.getCommentToken=function(e){return this.getLineCommentToken(e)||this.getBlockCommentToken(e)},R.prototype.getLineCommentToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.LINE_COMMENT,regex:this.LINE_COMMENT_REGEX})},R.prototype.getBlockCommentToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.BLOCK_COMMENT,regex:this.BLOCK_COMMENT_REGEX})},R.prototype.getStringToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.STRING,regex:this.STRING_REGEX})},R.prototype.getOpenParenToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.OPEN_PAREN,regex:this.OPEN_PAREN_REGEX})},R.prototype.getCloseParenToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.CLOSE_PAREN,regex:this.CLOSE_PAREN_REGEX})},R.prototype.getPlaceholderToken=function(e){return this.getIdentNamedPlaceholderToken(e)||this.getStringNamedPlaceholderToken(e)||this.getIndexedPlaceholderToken(e)},R.prototype.getServerVariableToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.SERVERVARIABLE,regex:/(^@@\w+)/iu})},R.prototype.getIdentNamedPlaceholderToken=function(e){return this.getPlaceholderTokenWithKey({input:e,regex:this.IDENT_NAMED_PLACEHOLDER_REGEX,parseKey:function(n){return n.slice(1)}})},R.prototype.getStringNamedPlaceholderToken=function(e){var n=this;return this.getPlaceholderTokenWithKey({input:e,regex:this.STRING_NAMED_PLACEHOLDER_REGEX,parseKey:function(I){return n.getEscapedPlaceholderKey({key:I.slice(2,-1),quoteChar:I.slice(-1)})}})},R.prototype.getIndexedPlaceholderToken=function(e){return this.getPlaceholderTokenWithKey({input:e,regex:this.INDEXED_PLACEHOLDER_REGEX,parseKey:function(n){return n.slice(1)}})},R.prototype.getPlaceholderTokenWithKey=function(e){var n=e.input,I=e.regex,r=e.parseKey,E=this.getTokenOnFirstMatch({input:n,regex:I,type:O.TokenTypes.PLACEHOLDER});return E&&(E.key=r(E.value)),E},R.prototype.getEscapedPlaceholderKey=function(e){var n=e.key,I=e.quoteChar;return n.replace(new RegExp((0,o.default)("\\"+I),"gu"),I)},R.prototype.getNumberToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.NUMBER,regex:this.NUMBER_REGEX})},R.prototype.getOperatorToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.OPERATOR,regex:this.OPERATOR_REGEX})},R.prototype.getAmbiguosOperatorToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.OPERATOR,regex:this.AMBIGUOS_OPERATOR_REGEX})},R.prototype.getNoSpaceOperatorToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.NO_SPACE_OPERATOR,regex:this.NO_SPACE_OPERATOR_REGEX})},R.prototype.getReservedWordToken=function(e,n){if(!(n&&n.value&&n.value==="."))return this.getToplevelReservedToken(e)||this.getNewlineReservedToken(e)||this.getTopLevelReservedTokenNoIndent(e)||this.getPlainReservedToken(e)},R.prototype.getToplevelReservedToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.RESERVED_TOP_LEVEL,regex:this.RESERVED_TOP_LEVEL_REGEX})},R.prototype.getNewlineReservedToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.RESERVED_NEWLINE,regex:this.RESERVED_NEWLINE_REGEX})},R.prototype.getPlainReservedToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.RESERVED,regex:this.RESERVED_PLAIN_REGEX})},R.prototype.getTopLevelReservedTokenNoIndent=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.RESERVED_TOP_LEVEL_NO_INDENT,regex:this.RESERVED_TOP_LEVEL_NO_INDENT_REGEX})},R.prototype.getWordToken=function(e){return this.getTokenOnFirstMatch({input:e,type:O.TokenTypes.WORD,regex:this.WORD_REGEX})},R.prototype.getTokenOnFirstMatch=function(e){var n=e.input,I=e.type,r=e.regex,E=n.match(r);if(E)return{type:I,value:E[1]}},R}();A.default=i})(_);var P={},c={},U={};(function(A){A.__esModule=!0;var N=function(o){return o===void 0&&(o=[]),o[o.length-1]};A.default=N})(U);(function(A){var N=s&&s.__importDefault||function(e){return e&&e.__esModule?e:{default:e}};A.__esModule=!0;var o=N(U),O="top-level",i="block-level",R=function(){function e(n){this.indent=n,this.indentTypes=[],this.indent=n||"  "}return e.prototype.getIndent=function(){return new Array(this.indentTypes.length).fill(this.indent).join("")},e.prototype.increaseTopLevel=function(){this.indentTypes.push(O)},e.prototype.increaseBlockLevel=function(){this.indentTypes.push(i)},e.prototype.decreaseTopLevel=function(){(0,o.default)(this.indentTypes)===O&&this.indentTypes.pop()},e.prototype.decreaseBlockLevel=function(){for(;this.indentTypes.length>0;){var n=this.indentTypes.pop();if(n!==O)break}},e.prototype.resetIndentation=function(){this.indentTypes=[]},e}();A.default=R})(c);var d={};(function(A){A.__esModule=!0;var N=C,o=50,O=function(){function i(){this.level=0}return i.prototype.beginIfPossible=function(R,e){this.level===0&&this.isInlineBlock(R,e)?this.level=1:this.level>0?this.level++:this.level=0},i.prototype.end=function(){this.level--},i.prototype.isActive=function(){return this.level>0},i.prototype.isInlineBlock=function(R,e){for(var n=0,I=0,r=e;r<R.length;r++){var E=R[r];if(n+=E.value.length,n>o)return!1;if(E.type===N.TokenTypes.OPEN_PAREN)I++;else if(E.type===N.TokenTypes.CLOSE_PAREN&&(I--,I===0))return!0;if(this.isForbiddenToken(E))return!1}return!1},i.prototype.isForbiddenToken=function(R){var e=R.type,n=R.value;return e===N.TokenTypes.RESERVED_TOP_LEVEL||e===N.TokenTypes.RESERVED_NEWLINE||e===N.TokenTypes.LINE_COMMENT||e===N.TokenTypes.BLOCK_COMMENT||n===";"},i}();A.default=O})(d);var f={};(function(A){A.__esModule=!0;var N=function(){function o(O){this.params=O,this.index=0,this.params=O}return o.prototype.get=function(O){var i=O.key,R=O.value;return this.params?i?this.params[i]:this.params[this.index++]:R},o}();A.default=N})(f);(function(A){var N=s&&s.__importDefault||function(r){return r&&r.__esModule?r:{default:r}};A.__esModule=!0;var o=C,O=N(c),i=N(d),R=N(f),e=[" ","	"],n=function(r){for(var E=r.length-1;E>=0&&e.includes(r[E]);)E--;return r.substring(0,E+1)},I=function(){function r(E,t,T){this.cfg=E,this.tokenizer=t,this.tokenOverride=T,this.tokens=[],this.previousReservedWord={type:null,value:null},this.previousNonWhiteSpace={type:null,value:null},this.index=0,this.indentation=new O.default(this.cfg.indent),this.inlineBlock=new i.default,this.params=new R.default(this.cfg.params)}return r.prototype.format=function(E){this.tokens=this.tokenizer.tokenize(E);var t=this.getFormattedQueryFromTokens();return t.trim()},r.prototype.getFormattedQueryFromTokens=function(){var E=this,t="";return this.tokens.forEach(function(T,S){E.index=S,E.tokenOverride&&(T=E.tokenOverride(T,E.previousReservedWord)||T),T.type===o.TokenTypes.WHITESPACE?t=E.formatWhitespace(T,t):T.type===o.TokenTypes.LINE_COMMENT?t=E.formatLineComment(T,t):T.type===o.TokenTypes.BLOCK_COMMENT?t=E.formatBlockComment(T,t):T.type===o.TokenTypes.RESERVED_TOP_LEVEL||T.type===o.TokenTypes.RESERVED_TOP_LEVEL_NO_INDENT||T.type===o.TokenTypes.RESERVED_NEWLINE||T.type===o.TokenTypes.RESERVED?t=E.formatReserved(T,t):T.type===o.TokenTypes.OPEN_PAREN?t=E.formatOpeningParentheses(T,t):T.type===o.TokenTypes.CLOSE_PAREN?t=E.formatClosingParentheses(T,t):T.type===o.TokenTypes.NO_SPACE_OPERATOR?t=E.formatWithoutSpaces(T,t):T.type===o.TokenTypes.PLACEHOLDER||T.type===o.TokenTypes.SERVERVARIABLE?t=E.formatPlaceholder(T,t):T.value===","?t=E.formatComma(T,t):T.value===":"?t=E.formatWithSpaceAfter(T,t):T.value==="."?t=E.formatWithoutSpaces(T,t):T.value===";"?t=E.formatQuerySeparator(T,t):t=E.formatWithSpaces(T,t),T.type!==o.TokenTypes.WHITESPACE&&(E.previousNonWhiteSpace=T)}),t},r.prototype.formatWhitespace=function(E,t){return this.cfg.linesBetweenQueries==="preserve"&&/((\r\n|\n)(\r\n|\n)+)/u.test(E.value)&&this.previousToken().value===";"?t.replace(/(\n|\r\n)$/u,"")+E.value:t},r.prototype.formatReserved=function(E,t){return E.type===o.TokenTypes.RESERVED_NEWLINE&&this.previousReservedWord&&this.previousReservedWord.value&&E.value.toUpperCase()==="AND"&&this.previousReservedWord.value.toUpperCase()==="BETWEEN"&&(E.type=o.TokenTypes.RESERVED),E.type===o.TokenTypes.RESERVED_TOP_LEVEL?t=this.formatTopLevelReservedWord(E,t):E.type===o.TokenTypes.RESERVED_TOP_LEVEL_NO_INDENT?t=this.formatTopLevelReservedWordNoIndent(E,t):E.type===o.TokenTypes.RESERVED_NEWLINE?t=this.formatNewlineReservedWord(E,t):t=this.formatWithSpaces(E,t),this.previousReservedWord=E,t},r.prototype.formatLineComment=function(E,t){return this.addNewline(t+E.value)},r.prototype.formatBlockComment=function(E,t){return this.addNewline(this.addNewline(t)+this.indentComment(E.value))},r.prototype.indentComment=function(E){return E.replace(/\n[ \t]*/gu,`
`+this.indentation.getIndent()+" ")},r.prototype.formatTopLevelReservedWordNoIndent=function(E,t){return this.indentation.decreaseTopLevel(),t=this.addNewline(t)+this.equalizeWhitespace(this.formatReservedWord(E.value)),this.addNewline(t)},r.prototype.formatTopLevelReservedWord=function(E,t){var T=this.previousNonWhiteSpace.value!==","&&!["GRANT"].includes("".concat(this.previousNonWhiteSpace.value).toUpperCase());return T&&(this.indentation.decreaseTopLevel(),t=this.addNewline(t)),t=t+this.equalizeWhitespace(this.formatReservedWord(E.value))+" ",T&&this.indentation.increaseTopLevel(),t},r.prototype.formatNewlineReservedWord=function(E,t){return this.addNewline(t)+this.equalizeWhitespace(this.formatReservedWord(E.value))+" "},r.prototype.equalizeWhitespace=function(E){return E.replace(/\s+/gu," ")},r.prototype.formatOpeningParentheses=function(E,t){E.value=this.formatCase(E.value);var T=this.previousToken().type;return T!==o.TokenTypes.WHITESPACE&&T!==o.TokenTypes.OPEN_PAREN&&T!==o.TokenTypes.LINE_COMMENT&&(t=n(t)),t+=E.value,this.inlineBlock.beginIfPossible(this.tokens,this.index),this.inlineBlock.isActive()||(this.indentation.increaseBlockLevel(),t=this.addNewline(t)),t},r.prototype.formatClosingParentheses=function(E,t){return E.value=this.formatCase(E.value),this.inlineBlock.isActive()?(this.inlineBlock.end(),this.formatWithSpaceAfter(E,t)):(this.indentation.decreaseBlockLevel(),this.formatWithSpaces(E,this.addNewline(t)))},r.prototype.formatPlaceholder=function(E,t){return t+this.params.get(E)+" "},r.prototype.formatComma=function(E,t){return t=n(t)+E.value+" ",this.inlineBlock.isActive()||/^LIMIT$/iu.test(this.previousReservedWord.value)?t:this.addNewline(t)},r.prototype.formatWithSpaceAfter=function(E,t){return n(t)+E.value+" "},r.prototype.formatWithoutSpaces=function(E,t){return n(t)+E.value},r.prototype.formatWithSpaces=function(E,t){var T=E.type===o.TokenTypes.RESERVED?this.formatReservedWord(E.value):E.value;return t+T+" "},r.prototype.formatReservedWord=function(E){return this.formatCase(E)},r.prototype.formatQuerySeparator=function(E,t){this.indentation.resetIndentation();var T=`
`;return this.cfg.linesBetweenQueries!=="preserve"&&(T=`
`.repeat(this.cfg.linesBetweenQueries||1)),n(t)+E.value+T},r.prototype.addNewline=function(E){return E=n(E),E.endsWith(`
`)||(E+=`
`),E+this.indentation.getIndent()},r.prototype.previousToken=function(){return this.tokens[this.index-1]||{type:null,value:null}},r.prototype.formatCase=function(E){return this.cfg.reservedWordCase==="upper"?E.toUpperCase():this.cfg.reservedWordCase==="lower"?E.toLowerCase():E},r}();A.default=I})(P);(function(A){var N=s&&s.__importDefault||function(R){return R&&R.__esModule?R:{default:R}};A.__esModule=!0;var o=N(_),O=N(P),i=function(){function R(e){this.cfg=e}return R.prototype.format=function(e){return new O.default(this.cfg,this.tokenizer(),this.tokenOverride).format(e)},R.prototype.tokenize=function(e){return this.tokenizer().tokenize(e)},R.prototype.tokenizer=function(){return new o.default(this.getTokenizerConfig())},R}();A.default=i})(a);(function(A){var N=s&&s.__extends||function(){var r=function(E,t){return r=Object.setPrototypeOf||{__proto__:[]}instanceof Array&&function(T,S){T.__proto__=S}||function(T,S){for(var L in S)Object.prototype.hasOwnProperty.call(S,L)&&(T[L]=S[L])},r(E,t)};return function(E,t){if(typeof t!="function"&&t!==null)throw new TypeError("Class extends value "+String(t)+" is not a constructor or null");r(E,t);function T(){this.constructor=E}E.prototype=t===null?Object.create(t):(T.prototype=t.prototype,new T)}}(),o=s&&s.__importDefault||function(r){return r&&r.__esModule?r:{default:r}};A.__esModule=!0;var O=o(a),i=function(r){N(E,r);function E(){return r!==null&&r.apply(this,arguments)||this}return E.prototype.getTokenizerConfig=function(){return{reservedWords:R,reservedTopLevelWords:e,reservedNewlineWords:I,reservedTopLevelWordsNoIndent:n,stringTypes:['""',"''","``","[]"],openParens:["("],closeParens:[")"],indexedPlaceholderTypes:["?"],namedPlaceholderTypes:[":"],lineCommentTypes:["--"],specialWordChars:["#","@"]}},E}(O.default);A.default=i;var R=["ABS","ACTIVATE","ALIAS","ALL","ALLOCATE","ALLOW","ALTER","ANY","ARE","ARRAY","AS","ASC","ASENSITIVE","ASSOCIATE","ASUTIME","ASYMMETRIC","AT","ATOMIC","ATTRIBUTES","AUDIT","AUTHORIZATION","AUX","AUXILIARY","AVG","BEFORE","BEGIN","BETWEEN","BIGINT","BINARY","BLOB","BOOLEAN","BOTH","BUFFERPOOL","BY","CACHE","CALL","CALLED","CAPTURE","CARDINALITY","CASCADED","CASE","CAST","CCSID","CEIL","CEILING","CHAR","CHARACTER","CHARACTER_LENGTH","CHAR_LENGTH","CHECK","CLOB","CLONE","CLOSE","CLUSTER","COALESCE","COLLATE","COLLECT","COLLECTION","COLLID","COLUMN","COMMENT","COMMIT","CONCAT","CONDITION","CONNECT","CONNECTION","CONSTRAINT","CONTAINS","CONTINUE","CONVERT","CORR","CORRESPONDING","COUNT","COUNT_BIG","COVAR_POP","COVAR_SAMP","CREATE","CROSS","CUBE","CUME_DIST","CURRENT","CURRENT_DATE","CURRENT_DEFAULT_TRANSFORM_GROUP","CURRENT_LC_CTYPE","CURRENT_PATH","CURRENT_ROLE","CURRENT_SCHEMA","CURRENT_SERVER","CURRENT_TIME","CURRENT_TIMESTAMP","CURRENT_TIMEZONE","CURRENT_TRANSFORM_GROUP_FOR_TYPE","CURRENT_USER","CURSOR","CYCLE","DATA","DATABASE","DATAPARTITIONNAME","DATAPARTITIONNUM","DATE","DAY","DAYS","DB2GENERAL","DB2GENRL","DB2SQL","DBINFO","DBPARTITIONNAME","DBPARTITIONNUM","DEALLOCATE","DEC","DECIMAL","DECLARE","DEFAULT","DEFAULTS","DEFINITION","DELETE","DENSERANK","DENSE_RANK","DEREF","DESCRIBE","DESCRIPTOR","DETERMINISTIC","DIAGNOSTICS","DISABLE","DISALLOW","DISCONNECT","DISTINCT","DO","DOCUMENT","DOUBLE","DROP","DSSIZE","DYNAMIC","EACH","EDITPROC","ELEMENT","ELSE","ELSEIF","ENABLE","ENCODING","ENCRYPTION","END","END-EXEC","ENDING","ERASE","ESCAPE","EVERY","EXCEPTION","EXCLUDING","EXCLUSIVE","EXEC","EXECUTE","EXISTS","EXIT","EXP","EXPLAIN","EXTENDED","EXTERNAL","EXTRACT","FALSE","FENCED","FETCH","FIELDPROC","FILE","FILTER","FINAL","FIRST","FLOAT","FLOOR","FOR","FOREIGN","FREE","FULL","FUNCTION","FUSION","GENERAL","GENERATED","GET","GLOBAL","GOTO","GRANT","GRAPHIC","GROUP","GROUPING","HANDLER","HASH","HASHED_VALUE","HINT","HOLD","HOUR","HOURS","IDENTITY","IF","IMMEDIATE","IN","INCLUDING","INCLUSIVE","INCREMENT","INDEX","INDICATOR","INDICATORS","INF","INFINITY","INHERIT","INNER","INOUT","INSENSITIVE","INSERT","INT","INTEGER","INTEGRITY","INTERSECTION","INTERVAL","INTO","IS","ISOBID","ISOLATION","ITERATE","JAR","JAVA","KEEP","KEY","LABEL","LANGUAGE","LARGE","LATERAL","LC_CTYPE","LEADING","LEAVE","LEFT","LIKE","LINKTYPE","LN","LOCAL","LOCALDATE","LOCALE","LOCALTIME","LOCALTIMESTAMP","LOCATOR","LOCATORS","LOCK","LOCKMAX","LOCKSIZE","LONG","LOOP","LOWER","MAINTAINED","MATCH","MATERIALIZED","MAX","MAXVALUE","MEMBER","MERGE","METHOD","MICROSECOND","MICROSECONDS","MIN","MINUTE","MINUTES","MINVALUE","MOD","MODE","MODIFIES","MODULE","MONTH","MONTHS","MULTISET","NAN","NATIONAL","NATURAL","NCHAR","NCLOB","NEW","NEW_TABLE","NEXTVAL","NO","NOCACHE","NOCYCLE","NODENAME","NODENUMBER","NOMAXVALUE","NOMINVALUE","NONE","NOORDER","NORMALIZE","NORMALIZED","NOT","NULL","NULLIF","NULLS","NUMERIC","NUMPARTS","OBID","OCTET_LENGTH","OF","OFFSET","OLD","OLD_TABLE","ON","ONLY","OPEN","OPTIMIZATION","OPTIMIZE","OPTION","ORDER","OUT","OUTER","OVER","OVERLAPS","OVERLAY","OVERRIDING","PACKAGE","PADDED","PAGESIZE","PARAMETER","PART","PARTITION","PARTITIONED","PARTITIONING","PARTITIONS","PASSWORD","PATH","PERCENTILE_CONT","PERCENTILE_DISC","PERCENT_RANK","PIECESIZE","PLAN","POSITION","POWER","PRECISION","PREPARE","PREVVAL","PRIMARY","PRIQTY","PRIVILEGES","PROCEDURE","PROGRAM","PSID","PUBLIC","QUERY","QUERYNO","RANGE","RANK","READ","READS","REAL","RECOVERY","RECURSIVE","REF","REFERENCES","REFERENCING","REFRESH","REGR_AVGX","REGR_AVGY","REGR_COUNT","REGR_INTERCEPT","REGR_R2","REGR_SLOPE","REGR_SXX","REGR_SXY","REGR_SYY","RELEASE","RENAME","REPEAT","RESET","RESIGNAL","RESTART","RESTRICT","RESULT","RESULT_SET_LOCATOR","RETURN","RETURNS","REVOKE","RIGHT","ROLE","ROLLBACK","ROLLUP","ROUND_CEILING","ROUND_DOWN","ROUND_FLOOR","ROUND_HALF_DOWN","ROUND_HALF_EVEN","ROUND_HALF_UP","ROUND_UP","ROUTINE","ROW","ROWNUMBER","ROWS","ROWSET","ROW_NUMBER","RRN","RUN","SAVEPOINT","SCHEMA","SCOPE","SCRATCHPAD","SCROLL","SEARCH","SECOND","SECONDS","SECQTY","SECURITY","SENSITIVE","SEQUENCE","SESSION","SESSION_USER","SIGNAL","SIMILAR","SIMPLE","SMALLINT","SNAN","SOME","SOURCE","SPECIFIC","SPECIFICTYPE","SQL","SQLEXCEPTION","SQLID","SQLSTATE","SQLWARNING","SQRT","STACKED","STANDARD","START","STARTING","STATEMENT","STATIC","STATMENT","STAY","STDDEV_POP","STDDEV_SAMP","STOGROUP","STORES","STYLE","SUBMULTISET","SUBSTRING","SUM","SUMMARY","SYMMETRIC","SYNONYM","SYSFUN","SYSIBM","SYSPROC","SYSTEM","SYSTEM_USER","TABLE","TABLESAMPLE","TABLESPACE","THEN","TIME","TIMESTAMP","TIMEZONE_HOUR","TIMEZONE_MINUTE","TO","TRAILING","TRANSACTION","TRANSLATE","TRANSLATION","TREAT","TRIGGER","TRIM","TRUE","TRUNCATE","TYPE","UESCAPE","UNDO","UNIQUE","UNKNOWN","UNNEST","UNTIL","UPPER","USAGE","USER","USING","VALIDPROC","VALUE","VARCHAR","VARIABLE","VARIANT","VARYING","VAR_POP","VAR_SAMP","VCAT","VERSION","VIEW","VOLATILE","VOLUMES","WHEN","WHENEVER","WHILE","WIDTH_BUCKET","WINDOW","WITH","WITHIN","WITHOUT","WLM","WRITE","XMLELEMENT","XMLEXISTS","XMLNAMESPACES","YEAR","YEARS"],e=["ADD","AFTER","ALTER COLUMN","ALTER TABLE","DELETE FROM","EXCEPT","FETCH FIRST","FROM","GROUP BY","GO","HAVING","INSERT INTO","INTERSECT","LIMIT","ORDER BY","SELECT","SET CURRENT SCHEMA","SET SCHEMA","SET","UPDATE","VALUES","WHERE"],n=["INTERSECT","INTERSECT ALL","MINUS","UNION","UNION ALL"],I=["AND","CROSS JOIN","INNER JOIN","JOIN","LEFT JOIN","LEFT OUTER JOIN","OR","OUTER JOIN","RIGHT JOIN","RIGHT OUTER JOIN"]})(p);var M={};(function(A){var N=s&&s.__extends||function(){var r=function(E,t){return r=Object.setPrototypeOf||{__proto__:[]}instanceof Array&&function(T,S){T.__proto__=S}||function(T,S){for(var L in S)Object.prototype.hasOwnProperty.call(S,L)&&(T[L]=S[L])},r(E,t)};return function(E,t){if(typeof t!="function"&&t!==null)throw new TypeError("Class extends value "+String(t)+" is not a constructor or null");r(E,t);function T(){this.constructor=E}E.prototype=t===null?Object.create(t):(T.prototype=t.prototype,new T)}}(),o=s&&s.__importDefault||function(r){return r&&r.__esModule?r:{default:r}};A.__esModule=!0;var O=o(a),i=function(r){N(E,r);function E(){return r!==null&&r.apply(this,arguments)||this}return E.prototype.getTokenizerConfig=function(){return{reservedWords:R,reservedTopLevelWords:e,reservedNewlineWords:I,reservedTopLevelWordsNoIndent:n,stringTypes:['""',"''","``"],openParens:["(","[","{"],closeParens:[")","]","}"],namedPlaceholderTypes:["$"],lineCommentTypes:["#","--"],specialWordChars:[]}},E}(O.default);A.default=i;var R=["ALL","ALTER","ANALYZE","AND","ANY","ARRAY","AS","ASC","BEGIN","BETWEEN","BINARY","BOOLEAN","BREAK","BUCKET","BUILD","BY","CALL","CASE","CAST","CLUSTER","COLLATE","COLLECTION","COMMIT","CONNECT","CONTINUE","CORRELATE","COVER","CREATE","DATABASE","DATASET","DATASTORE","DECLARE","DECREMENT","DELETE","DERIVED","DESC","DESCRIBE","DISTINCT","DO","DROP","EACH","ELEMENT","ELSE","END","EVERY","EXCEPT","EXCLUDE","EXECUTE","EXISTS","EXPLAIN","FALSE","FETCH","FIRST","FLATTEN","FOR","FORCE","FROM","FUNCTION","GRANT","GROUP","GSI","HAVING","IF","IGNORE","ILIKE","IN","INCLUDE","INCREMENT","INDEX","INFER","INLINE","INNER","INSERT","INTERSECT","INTO","IS","JOIN","KEY","KEYS","KEYSPACE","KNOWN","LAST","LEFT","LET","LETTING","LIKE","LIMIT","LSM","MAP","MAPPING","MATCHED","MATERIALIZED","MERGE","MISSING","NAMESPACE","NEST","NOT","NULL","NUMBER","OBJECT","OFFSET","ON","OPTION","OR","ORDER","OUTER","OVER","PARSE","PARTITION","PASSWORD","PATH","POOL","PREPARE","PRIMARY","PRIVATE","PRIVILEGE","PROCEDURE","PUBLIC","RAW","REALM","REDUCE","RENAME","RETURN","RETURNING","REVOKE","RIGHT","ROLE","ROLLBACK","SATISFIES","SCHEMA","SELECT","SELF","SEMI","SET","SHOW","SOME","START","STATISTICS","STRING","SYSTEM","THEN","TO","TRANSACTION","TRIGGER","TRUE","TRUNCATE","UNDER","UNION","UNIQUE","UNKNOWN","UNNEST","UNSET","UPDATE","UPSERT","USE","USER","USING","VALIDATE","VALUE","VALUED","VALUES","VIA","VIEW","WHEN","WHERE","WHILE","WITH","WITHIN","WORK","XOR"],e=["DELETE FROM","EXCEPT ALL","EXCEPT","EXPLAIN DELETE FROM","EXPLAIN UPDATE","EXPLAIN UPSERT","FROM","GROUP BY","HAVING","INFER","INSERT INTO","LET","LIMIT","MERGE","NEST","ORDER BY","PREPARE","SELECT","SET CURRENT SCHEMA","SET SCHEMA","SET","UNNEST","UPDATE","UPSERT","USE KEYS","VALUES","WHERE"],n=["INTERSECT","INTERSECT ALL","MINUS","UNION","UNION ALL"],I=["AND","INNER JOIN","JOIN","LEFT JOIN","LEFT OUTER JOIN","OR","OUTER JOIN","RIGHT JOIN","RIGHT OUTER JOIN","XOR"]})(M);var h={};(function(A){var N=s&&s.__extends||function(){var E=function(t,T){return E=Object.setPrototypeOf||{__proto__:[]}instanceof Array&&function(S,L){S.__proto__=L}||function(S,L){for(var u in L)Object.prototype.hasOwnProperty.call(L,u)&&(S[u]=L[u])},E(t,T)};return function(t,T){if(typeof T!="function"&&T!==null)throw new TypeError("Class extends value "+String(T)+" is not a constructor or null");E(t,T);function S(){this.constructor=t}t.prototype=T===null?Object.create(T):(S.prototype=T.prototype,new S)}}(),o=s&&s.__importDefault||function(E){return E&&E.__esModule?E:{default:E}};A.__esModule=!0;var O=o(a),i=C,R=function(E){N(t,E);function t(){var T=E!==null&&E.apply(this,arguments)||this;return T.tokenOverride=function(S,L){if(S.type===i.TokenTypes.RESERVED_TOP_LEVEL&&L.value&&S.value.toUpperCase()==="SET"&&L.value.toUpperCase()==="BY")return S.type=i.TokenTypes.RESERVED,S},T}return t.prototype.getTokenizerConfig=function(){return{reservedWords:e,reservedTopLevelWords:n,reservedNewlineWords:r,reservedTopLevelWordsNoIndent:I,stringTypes:['""',"N''","''","``"],openParens:["(","CASE"],closeParens:[")","END"],indexedPlaceholderTypes:["?"],namedPlaceholderTypes:[":"],lineCommentTypes:["--"],specialWordChars:["_","$","#",".","@"]}},t}(O.default);A.default=R;var e=["A","ACCESSIBLE","AGENT","AGGREGATE","ALL","ALTER","ANY","ARRAY","AS","ASC","AT","ATTRIBUTE","AUTHID","AVG","BETWEEN","BFILE_BASE","BINARY_INTEGER","BINARY","BLOB_BASE","BLOCK","BODY","BOOLEAN","BOTH","BOUND","BREADTH","BULK","BY","BYTE","C","CALL","CALLING","CASCADE","CASE","CHAR_BASE","CHAR","CHARACTER","CHARSET","CHARSETFORM","CHARSETID","CHECK","CLOB_BASE","CLONE","CLOSE","CLUSTER","CLUSTERS","COALESCE","COLAUTH","COLLECT","COLUMNS","COMMENT","COMMIT","COMMITTED","COMPILED","COMPRESS","CONNECT","CONSTANT","CONSTRUCTOR","CONTEXT","CONTINUE","CONVERT","COUNT","CRASH","CREATE","CREDENTIAL","CURRENT","CURRVAL","CURSOR","CUSTOMDATUM","DANGLING","DATA","DATE_BASE","DATE","DAY","DECIMAL","DEFAULT","DEFINE","DELETE","DEPTH","DESC","DETERMINISTIC","DIRECTORY","DISTINCT","DO","DOUBLE","DROP","DURATION","ELEMENT","ELSIF","EMPTY","END","ESCAPE","EXCEPTIONS","EXCLUSIVE","EXECUTE","EXISTS","EXIT","EXTENDS","EXTERNAL","EXTRACT","FALSE","FETCH","FINAL","FIRST","FIXED","FLOAT","FOR","FORALL","FORCE","FROM","FUNCTION","GENERAL","GOTO","GRANT","GROUP","HASH","HEAP","HIDDEN","HOUR","IDENTIFIED","IF","IMMEDIATE","IN","INCLUDING","INDEX","INDEXES","INDICATOR","INDICES","INFINITE","INSTANTIABLE","INT","INTEGER","INTERFACE","INTERVAL","INTO","INVALIDATE","IS","ISOLATION","JAVA","LANGUAGE","LARGE","LEADING","LENGTH","LEVEL","LIBRARY","LIKE","LIKE2","LIKE4","LIKEC","LIMITED","LOCAL","LOCK","LONG","MAP","MAX","MAXLEN","MEMBER","MERGE","MIN","MINUTE","MLSLABEL","MOD","MODE","MONTH","MULTISET","NAME","NAN","NATIONAL","NATIVE","NATURAL","NATURALN","NCHAR","NEW","NEXTVAL","NOCOMPRESS","NOCOPY","NOT","NOWAIT","NULL","NULLIF","NUMBER_BASE","NUMBER","OBJECT","OCICOLL","OCIDATE","OCIDATETIME","OCIDURATION","OCIINTERVAL","OCILOBLOCATOR","OCINUMBER","OCIRAW","OCIREF","OCIREFCURSOR","OCIROWID","OCISTRING","OCITYPE","OF","OLD","ON","ONLY","OPAQUE","OPEN","OPERATOR","OPTION","ORACLE","ORADATA","ORDER","ORGANIZATION","ORLANY","ORLVARY","OTHERS","OUT","OVERLAPS","OVERRIDING","PACKAGE","PARALLEL_ENABLE","PARAMETER","PARAMETERS","PARENT","PARTITION","PASCAL","PCTFREE","PIPE","PIPELINED","PLS_INTEGER","PLUGGABLE","POSITIVE","POSITIVEN","PRAGMA","PRECISION","PRIOR","PRIVATE","PROCEDURE","PUBLIC","RAISE","RANGE","RAW","READ","REAL","RECORD","REF","REFERENCE","RELEASE","RELIES_ON","REM","REMAINDER","RENAME","RESOURCE","RESULT_CACHE","RESULT","RETURN","RETURNING","REVERSE","REVOKE","ROLLBACK","ROW","ROWID","ROWNUM","ROWTYPE","SAMPLE","SAVE","SAVEPOINT","SB1","SB2","SB4","SEARCH","SECOND","SEGMENT","SELF","SEPARATE","SEQUENCE","SERIALIZABLE","SHARE","SHORT","SIZE_T","SIZE","SMALLINT","SOME","SPACE","SPARSE","SQL","SQLCODE","SQLDATA","SQLERRM","SQLNAME","SQLSTATE","STANDARD","START","STATIC","STDDEV","STORED","STRING","STRUCT","STYLE","SUBMULTISET","SUBPARTITION","SUBSTITUTABLE","SUBTYPE","SUCCESSFUL","SUM","SYNONYM","SYSDATE","TABAUTH","TABLE","TDO","THE","THEN","TIME","TIMESTAMP","TIMEZONE_ABBR","TIMEZONE_HOUR","TIMEZONE_MINUTE","TIMEZONE_REGION","TO","TRAILING","TRANSACTION","TRANSACTIONAL","TRIGGER","TRUE","TRUSTED","TYPE","UB1","UB2","UB4","UID","UNDER","UNIQUE","UNPLUG","UNSIGNED","UNTRUSTED","USE","USER","USING","VALIDATE","VALIST","VALUE","VARCHAR","VARCHAR2","VARIABLE","VARIANCE","VARRAY","VARYING","VIEW","VIEWS","VOID","WHENEVER","WHILE","WITH","WORK","WRAPPED","WRITE","YEAR","ZONE"],n=["ADD","ALTER COLUMN","ALTER TABLE","BEGIN","CONNECT BY","DECLARE","DELETE FROM","DELETE","END","EXCEPT","EXCEPTION","FETCH FIRST","FROM","GROUP BY","HAVING","INSERT INTO","INSERT","LIMIT","LOOP","MODIFY","ORDER BY","SELECT","SET CURRENT SCHEMA","SET SCHEMA","SET","START WITH","UPDATE","VALUES","WHERE"],I=["INTERSECT","INTERSECT ALL","MINUS","UNION","UNION ALL"],r=["AND","CROSS APPLY","CROSS JOIN","ELSE","END","INNER JOIN","JOIN","LEFT JOIN","LEFT OUTER JOIN","OR","OUTER APPLY","OUTER JOIN","RIGHT JOIN","RIGHT OUTER JOIN","WHEN","XOR"]})(h);var v={};(function(A){var N=s&&s.__extends||function(){var r=function(E,t){return r=Object.setPrototypeOf||{__proto__:[]}instanceof Array&&function(T,S){T.__proto__=S}||function(T,S){for(var L in S)Object.prototype.hasOwnProperty.call(S,L)&&(T[L]=S[L])},r(E,t)};return function(E,t){if(typeof t!="function"&&t!==null)throw new TypeError("Class extends value "+String(t)+" is not a constructor or null");r(E,t);function T(){this.constructor=E}E.prototype=t===null?Object.create(t):(T.prototype=t.prototype,new T)}}(),o=s&&s.__importDefault||function(r){return r&&r.__esModule?r:{default:r}};A.__esModule=!0;var O=o(a),i=function(r){N(E,r);function E(){return r!==null&&r.apply(this,arguments)||this}return E.prototype.getTokenizerConfig=function(){return{reservedWords:R,reservedTopLevelWords:e,reservedNewlineWords:I,reservedTopLevelWordsNoIndent:n,stringTypes:['""',"N''","''","``","[]","E''"],openParens:["(","CASE"],closeParens:[")","END"],indexedPlaceholderTypes:["?"],namedPlaceholderTypes:["@",":","%","$"],lineCommentTypes:["#","--"],specialWordChars:[]}},E}(O.default);A.default=i;var R=["ACCESSIBLE","ACTION","AGAINST","AGGREGATE","ALGORITHM","ALL","ALTER","ANALYSE","ANALYZE","AS","ASC","AUTOCOMMIT","AUTO_INCREMENT","BACKUP","BEGIN","BETWEEN","BINLOG","BOTH","CASCADE","CASE","CHANGE","CHANGED","CHARACTER SET","CHARSET","CHECK","CHECKSUM","COLLATE","COLLATION","COLUMN","COLUMNS","COMMENT","COMMIT","COMMITTED","COMPRESSED","CONCURRENT","CONSTRAINT","CONTAINS","CONVERT","COUNT","CREATE","CROSS","CURRENT_TIMESTAMP","DATABASE","DATABASES","DAY_HOUR","DAY_MINUTE","DAY_SECOND","DAY","DEFAULT","DEFINER","DELAYED","DELETE","DESC","DESCRIBE","DETERMINISTIC","DISTINCT","DISTINCTROW","DIV","DO","DROP","DUMPFILE","DUPLICATE","DYNAMIC","ELSE","ENCLOSED","END","ENGINE","ENGINES","ENGINE_TYPE","ESCAPE","ESCAPED","EVENTS","EXEC","EXECUTE","EXISTS","EXPLAIN","EXTENDED","FAST","FETCH","FIELDS","FILE","FIRST","FIXED","FLUSH","FOR","FORCE","FOREIGN","FULL","FULLTEXT","FUNCTION","GLOBAL","GRANTS","GROUP_CONCAT","HEAP","HIGH_PRIORITY","HOSTS","HOUR","HOUR_MINUTE","HOUR_SECOND","IDENTIFIED","IF","IFNULL","IGNORE","IN","INDEX","INDEXES","INFILE","INSERT","INSERT_ID","INSERT_METHOD","INTERVAL","INTO","INVOKER","IS","ISOLATION","KEY","KEYS","KILL","LAST_INSERT_ID","LEADING","LEVEL","LIKE","LINEAR","LINES","LOAD","LOCAL","LOCK","LOCKS","LOGS","LOW_PRIORITY","MARIA","MASTER","MASTER_CONNECT_RETRY","MASTER_HOST","MASTER_LOG_FILE","MATCH","MAX_CONNECTIONS_PER_HOUR","MAX_QUERIES_PER_HOUR","MAX_ROWS","MAX_UPDATES_PER_HOUR","MAX_USER_CONNECTIONS","MEDIUM","MERGE","MINUTE","MINUTE_SECOND","MIN_ROWS","MODE","MONTH","MRG_MYISAM","MYISAM","NAMES","NATURAL","NOT","NOW()","NULL","OFFSET","ON DELETE","ON UPDATE","ON","ONLY","OPEN","OPTIMIZE","OPTION","OPTIONALLY","OUTFILE","PACK_KEYS","PAGE","PARTIAL","PARTITION","PARTITIONS","PASSWORD","PRIMARY","PRIVILEGES","PROCEDURE","PROCESS","PROCESSLIST","PURGE","QUICK","RAID0","RAID_CHUNKS","RAID_CHUNKSIZE","RAID_TYPE","RANGE","READ","READ_ONLY","READ_WRITE","REFERENCES","REGEXP","RELOAD","RENAME","REPAIR","REPEATABLE","REPLACE","REPLICATION","RESET","RESTORE","RESTRICT","RETURN","RETURNS","REVOKE","RLIKE","ROLLBACK","ROW","ROWS","ROW_FORMAT","SECOND","SECURITY","SEPARATOR","SERIALIZABLE","SESSION","SHARE","SHOW","SHUTDOWN","SLAVE","SONAME","SOUNDS","SQL","SQL_AUTO_IS_NULL","SQL_BIG_RESULT","SQL_BIG_SELECTS","SQL_BIG_TABLES","SQL_BUFFER_RESULT","SQL_CACHE","SQL_CALC_FOUND_ROWS","SQL_LOG_BIN","SQL_LOG_OFF","SQL_LOG_UPDATE","SQL_LOW_PRIORITY_UPDATES","SQL_MAX_JOIN_SIZE","SQL_NO_CACHE","SQL_QUOTE_SHOW_CREATE","SQL_SAFE_UPDATES","SQL_SELECT_LIMIT","SQL_SLAVE_SKIP_COUNTER","SQL_SMALL_RESULT","SQL_WARNINGS","START","STARTING","STATUS","STOP","STORAGE","STRAIGHT_JOIN","STRING","STRIPED","SUPER","TABLE","TABLES","TEMPORARY","TERMINATED","THEN","TO","TRAILING","TRANSACTIONAL","TRIGGER","TRUE","TRUNCATE","TYPE","TYPES","UNCOMMITTED","UNIQUE","UNLOCK","UNSIGNED","USAGE","USE","USING","VARIABLES","VIEW","WHEN","WITH","WORK","WRITE","YEAR_MONTH"],e=["ADD","AFTER","ALTER COLUMN","ALTER TABLE","CREATE OR REPLACE","DECLARE","DELETE FROM","EXCEPT","FETCH FIRST","FROM","GO","GRANT","GROUP BY","HAVING","INSERT INTO","INSERT","LIMIT","MODIFY","ORDER BY","RETURNING","SELECT","SET CURRENT SCHEMA","SET SCHEMA","SET","UPDATE","VALUES","WHERE"],n=["INTERSECT ALL","INTERSECT","MINUS","UNION ALL","UNION"],I=["AND","CROSS APPLY","CROSS JOIN","ELSE","INNER JOIN","FULL JOIN","FULL OUTER JOIN","LEFT JOIN","LEFT OUTER JOIN","NATURAL JOIN","OR","OUTER APPLY","OUTER JOIN","RENAME","RIGHT JOIN","RIGHT OUTER JOIN","JOIN","WHEN","XOR"]})(v);(function(A){var N=s&&s.__importDefault||function(I){return I&&I.__esModule?I:{default:I}};A.__esModule=!0,A.tokenize=A.format=void 0;var o=N(p),O=N(M),i=N(h),R=N(v),e=function(I,r){switch(r===void 0&&(r={}),r.language){case"db2":return new o.default(r).format(I);case"n1ql":return new O.default(r).format(I);case"pl/sql":return new i.default(r).format(I);case"sql":default:return new R.default(r).format(I)}};A.format=e;var n=function(I,r){return r===void 0&&(r={}),new R.default(r).tokenize(I)};A.tokenize=n,A.default={format:A.format,tokenize:A.tokenize}})(l);const F=G(l);export{F as s};
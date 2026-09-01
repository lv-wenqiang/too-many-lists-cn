# Miri

*紧张地笑*这个 unsafe 的东西太简单了，我不明白为什么大家都说它难。我们的程序运行得完美无缺。

> **旁白：**🙂

……对吧？

> **旁白：**🙂

嗯，我们现在写的是`unsafe`代码，所以编译器没法再那么好地帮我们抓错了。有可能这些测试只是*碰巧*通过了，而实际上程序在做某种不确定的事情。某种带着未定义行为味道的事情。

但我们能做什么呢？我们已经撬开窗户，溜出了 rustc 的教室。现在没人能帮我们了。

……等等，巷子里那个鬼鬼祟祟的人是谁？

*“嘿小孩，想解释点 Rust 代码吗？”*

什——不想？为什么，

*“这玩意儿野得很，老兄，它能验证你程序的实际动态执行是否符合 Rust 内存模型的语义。爽爆你的脑子……”*

什么？

*“它会检查你有没有干出未定义行为。”*

我想我可以*就试一次*解释器。

*“你装了 rustup 吧？”*

我当然装了，它可是保持 Rust 工具链最新的*那个*工具！

```text
> rustup +nightly-2022-01-21 component add miri

info: syncing channel updates for 'nightly-2022-01-21-x86_64-pc-windows-msvc'
info: latest update on 2022-01-21, rust version 1.60.0-nightly (777bb86bc 2022-01-20)
info: downloading component 'cargo'
info: downloading component 'clippy'
info: downloading component 'rust-docs'
info: downloading component 'rust-std'
info: downloading component 'rustc'
info: downloading component 'rustfmt'
info: installing component 'cargo'
info: installing component 'clippy'
info: installing component 'rust-docs'
info: installing component 'rust-std'
info: installing component 'rustc'
info: installing component 'rustfmt'
info: downloading component 'miri'
info: installing component 'miri'
```

你刚才往我电脑上装了什么！？

*“好东西”*

> **旁白：**工具链版本这里有些奇怪的地方：
>
> 我们要装的这个工具`miri`，和 rustc 的内部实现结合得很紧密，
> 所以它只在 nightly 工具链上可用。
>
> `+nightly-2022-01-21`告诉`rustup`，我们想在那个日期的 Rust nightly 工具链上
> 安装 miri。我给出一个具体日期，是因为有时候 miri 会落后，
> 在某几个 nightly 上构建不出来。如果我们还没装过所指定的工具链，
> rustup 会自动下载我们用`+`指定的那一个。
>
> 2022-01-21 只是我知道支持 miri 的一个 nightly，你可以
> [在这个状态页面上](https://rust-lang.github.io/rustup-components-history/)查看。
> 如果你觉得自己运气好，直接用`+nightly`也行。
>
> 每当我们通过`cargo miri`调用 miri 时，我们同样会用这个`+`语法来指定
> 安装了 miri 的那个工具链。如果你不想每次都指定，
> 可以使用[`rustup override set`](https://rust-lang.github.io/rustup/overrides.html)。

```text
> cargo +nightly-2022-01-21 miri test

I will run `"cargo.exe" "install" "xargo"` to install
a recent enough xargo. Proceed? [Y/n]
```

呃，XARGO 到底是个什么鬼？

*“没事的，别管它。”*

```text
> y

    Updating crates.io index
  Installing xargo v0.3.24
...
    Finished release [optimized] target(s) in 10.65s
  Installing C:\Users\ninte\.cargo\bin\xargo-check.exe
  Installing C:\Users\ninte\.cargo\bin\xargo.exe
   Installed package `xargo v0.3.24` (executables `xargo-check.exe`, `xargo.exe`)

I will run `"rustup" "component" "add" "rust-src"` to install 
the `rust-src` component for the selected toolchain. Proceed? [Y/n]
```

呃？？？

*“谁不喜欢手头有一份 Rust 源代码呢？”*

```text
> y

info: downloading component 'rust-src'
info: installing component 'rust-src'
```

*“啊好了准备就绪，精彩的部分来了。”*

```text
   Compiling lists v0.1.0 (C:\Users\ninte\dev\tmp\lists)
    Finished test [unoptimized + debuginfo] target(s) in 0.25s
     Running unittests (lists-5cc11d9ee5c3e924.exe)

error: Undefined Behavior: trying to reborrow for Unique at alloc84055, 
       but parent tag <209678> does not have an appropriate item in 
       the borrow stack

   --> \lib\rustlib\src\rust\library\core\src\option.rs:846:18
    |
846 |             Some(x) => Some(f(x)),
    |                  ^ trying to reborrow for Unique at alloc84055, 
    |                    but parent tag <209678> does not have an 
    |                    appropriate item in the borrow stack
    |
    = help: this indicates a potential bug in the program: 
      it performed an invalid operation, but the rules it 
      violated are still experimental
    = help: see https://github.com/rust-lang/unsafe-code-guidelines/blob/master/wip/stacked-borrows.md 
      for further information

    = note: inside `std::option::Option::<std::boxed::Box<fifth::Node<i32>>>::map::<i32, [closure@src\fifth.rs:31:30: 40:10]>` at \lib\rustlib\src\rust\library\core\src\option.rs:846:18

note: inside `fifth::List::<i32>::pop` at src\fifth.rs:31:9
   --> src\fifth.rs:31:9
    |
31  | /         self.head.take().map(|head| {
32  | |             let head = *head;
33  | |             self.head = head.next;
34  | |
...   |
39  | |             head.elem
40  | |         })
    | |__________^
note: inside `fifth::test::basics` at src\fifth.rs:74:20
   --> src\fifth.rs:74:20
    |
74  |         assert_eq!(list.pop(), Some(1));
    |                    ^^^^^^^^^^
note: inside closure at src\fifth.rs:62:5
   --> src\fifth.rs:62:5
    |
61  |       #[test]
    |       ------- in this procedural macro expansion
62  | /     fn basics() {
63  | |         let mut list = List::new();
64  | |
65  | |         // Check empty list behaves right
...   |
96  | |         assert_eq!(list.pop(), None);
97  | |     }
    | |_____^
 ...
error: aborting due to previous error
```

哇哦。这错误可真够劲的。

*“对啊，瞧瞧这玩意儿。看着就爽。”*

谢谢你？

*“这瓶雌二醇也拿着吧，你之后会用得上的。”*

等等，为什么？

*“你马上就要开始思考内存模型了，相信我。”*

> **旁白：**那个神秘人随即变成一只狐狸，从墙上的洞里窜了出去。作者则盯着半空发了好几分钟的呆，试图消化刚刚发生的一切。


-------

巷子里那只神秘的狐狸说对的不只是我的性别：miri 真的是个好东西。

好了，那么 [miri](https://github.com/rust-lang/miri) 到底*是*什么？

> 一个用于 Rust 中层中间表示（MIR）的实验性解释器。它可以运行 cargo 项目的
> 二进制文件和测试套件，并检测出某些类别的未定义行为，例如：
>
> * 越界内存访问和释放后使用
> * 对未初始化数据的非法使用
> * 违反内建函数的前置条件（执行到了 unreachable_unchecked、
>   用重叠的区间调用 copy_nonoverlapping，等等）
> * 对齐不足的内存访问和引用
> * 违反某些基本的类型不变式（比如一个既不是 0 也不是 1 的 bool，
>   或者一个非法的枚举判别值）
> * 实验性：违反了管辖引用类型别名规则的 Stacked Borrows（堆叠借用）规则
> * 实验性：数据竞争（但不包括弱内存效应）
>
> 除此之外，Miri 还会告诉你内存泄漏的情况：当执行结束时仍有内存处于已分配状态，
> 而这块内存又无法从全局静态变量到达时，Miri 就会报错。
>
> ……
>
> 不过要注意，Miri 并不能捕捉到你程序中所有的未定义行为，也不能运行所有程序

太长不看版：它会解释执行你的程序，并在你*运行时*违反规则、干出未定义行为时发现这一点。这是必要的，因为未定义行为*通常*是运行时才发生的事情。如果问题能在编译期发现，编译器早就直接把它变成错误了！

如果你熟悉 ubsan 和 tsan 这类工具：它基本上就是把那些合到一块儿，而且更极端。

-------

现在 miri 正拿着一把刀吊在教室窗外。一把教学用的刀。

如果我们想让 miri 检查我们的工作，可以这样请它解释执行我们的测试套件

```text
> cargo +nightly-2022-01-21 miri test
```

现在我们来仔细看看它在我们课桌上刻了些什么：

```text
error: Undefined Behavior: trying to reborrow for Unique at alloc84055, but parent tag <209678> does not have an appropriate item in the borrow stack

   --> \lib\rustlib\src\rust\library\core\src\option.rs:846:18
    |
846 |             Some(x) => Some(f(x)),
    |                  ^ trying to reborrow for Unique at alloc84055, 
    |                    but parent tag <209678> does not have an 
    |                    appropriate item in the borrow stack
    |

    = help: this indicates a potential bug in the program: it 
      performed an invalid operation, but the rules it 
      violated are still experimental
    
    = help: see 
      https://github.com/rust-lang/unsafe-code-guidelines/blob/master/wip/stacked-borrows.md 
      for further information
```

好吧，我能看出我们犯了个错误，但这错误信息实在让人困惑。什么是“借用栈”？

我们将在下一节里试着搞清楚这个问题。
# Iter

好了，我们来试着实现 Iter。这一次我们没法指望 List 把我们想要的功能都提供好，
得自己动手了。我们想要的基本逻辑是：持有一个指针，指向下一次要产出的那个当前
节点。因为那个节点可能并不存在（链表是空的，或者我们已经迭代完了），
所以我们希望这个引用是一个 Option。每当产出一个元素，
我们就前进到当前节点的`next`节点。

好了，来试试看：

```rust ,ignore
pub struct Iter<T> {
    next: Option<&Node<T>>,
}

impl<T> List<T> {
    pub fn iter(&self) -> Iter<T> {
        Iter { next: self.head.map(|node| &node) }
    }
}

impl<T> Iterator for Iter<T> {
    type Item = &T;

    fn next(&mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.next.map(|node| &node);
            &node.elem
        })
    }
}
```

```text
> cargo build

error[E0106]: missing lifetime specifier
  --> src/second.rs:72:18
   |
72 |     next: Option<&Node<T>>,
   |                  ^ expected lifetime parameter

error[E0106]: missing lifetime specifier
  --> src/second.rs:82:17
   |
82 |     type Item = &T;
   |                 ^ expected lifetime parameter
```

老天。生命周期。我听说过这玩意儿。听说它们是噩梦。

我们来试点新东西：看到那个`error[E0106]`了吗？那是一个编译器错误码。
我们可以让 rustc 解释它们，用的就是`--explain`：

```text
> rustc --explain E0106
This error indicates that a lifetime is missing from a type. If it is an error
inside a function signature, the problem may be with failing to adhere to the
lifetime elision rules (see below).

Here are some simple examples of where you'll run into this error:

struct Foo { x: &bool }        // error
struct Foo<'a> { x: &'a bool } // correct

enum Bar { A(u8), B(&bool), }        // error
enum Bar<'a> { A(u8), B(&'a bool), } // correct

type MyStr = &str;        // error
type MyStr<'a> = &'a str; //correct
...

```

那个……呃，那并没有解释清楚多少（这些文档默认我们对 Rust 的理解比现在要好）。
不过看起来我们应该把那些`'a`加到结构体上？来试试。

```rust ,ignore
pub struct Iter<'a, T> {
    next: Option<&'a Node<T>>,
}
```

```text
> cargo build

error[E0106]: missing lifetime specifier
  --> src/second.rs:83:22
   |
83 | impl<T> Iterator for Iter<T> {
   |                      ^^^^^^^ expected lifetime parameter

error[E0106]: missing lifetime specifier
  --> src/second.rs:84:17
   |
84 |     type Item = &T;
   |                 ^ expected lifetime parameter

error: aborting due to 2 previous errors
```

好吧，我开始看出规律了……我们干脆把这些小家伙加到所有能加的地方：

```rust ,ignore
pub struct Iter<'a, T> {
    next: Option<&'a Node<T>>,
}

impl<'a, T> List<T> {
    pub fn iter(&'a self) -> Iter<'a, T> {
        Iter { next: self.head.map(|node| &'a node) }
    }
}

impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;
    fn next(&'a mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.next.map(|node| &'a node);
            &'a node.elem
        })
    }
}
```

```text
> cargo build

error: expected `:`, found `node`
  --> src/second.rs:77:47
   |
77 |         Iter { next: self.head.map(|node| &'a node) }
   |         ---- while parsing this struct        ^^^^ expected `:`

error: expected `:`, found `node`
  --> src/second.rs:85:50
   |
85 |             self.next = node.next.map(|node| &'a node);
   |                                                  ^^^^ expected `:`

error[E0063]: missing field `next` in initializer of `second::Iter<'_, _>`
  --> src/second.rs:77:9
   |
77 |         Iter { next: self.head.map(|node| &'a node) }
   |         ^^^^ missing `next`
```

老天。我们把 Rust 弄坏了。

也许我们真该搞清楚这个`'a`生命周期到底是个什么鬼东西。

生命周期能把很多人吓跑，因为它改变了我们自编程诞生之初就熟知并热爱的某样东西。
其实到目前为止我们一直设法躲开了生命周期，尽管它们自始至终都缠绕在我们的
程序里。

在垃圾回收（garbage collection）语言里生命周期是不必要的，因为垃圾回收器保证了一切都会魔法般地
活得足够久。而 Rust 中的大多数数据是*手动*管理的，所以这些数据需要另一套方案。
C 和 C++ 给了我们一个清楚的例子，说明如果放任人们随手获取指向栈上任意数据的
指针会发生什么：无处不在、无法收拾的不安全。这大致可以分为两类错误：

* 持有一个指向已经离开作用域的东西的指针
* 持有一个指向已经被改掉的东西的指针

生命周期解决了这两个问题，而且在 99% 的时间里，它们是以完全透明的方式做到的。

那么，生命周期到底是什么？

很简单，生命周期就是程序中某处一段代码区域（\~代码块/作用域）的名字。
就这么回事。当一个引用被标上某个生命周期时，我们是在说它必须在那*整个*区域内
都保持有效。不同的东西会对一个引用必须、以及能够保持有效多久提出各自的要求。
而整个生命周期系统，说到底不过是一个约束求解系统，它试图把每个引用的区域
最小化。如果它成功找到了一组满足所有约束的生命周期，你的程序就能编译通过！
否则你就会收到一个错误，说某个东西活得不够久。

在函数体内部你通常没法谈论生命周期，而且*反正*你也不会想谈。编译器掌握着完整
信息，能够推断出所有约束，找到最小的生命周期。然而在类型和 API 层面，
编译器*并没有*掌握全部信息。它需要你告诉它不同生命周期之间的关系，
这样它才能搞清楚你在干什么。

原则上，那些生命周期*也可以*被省略掉，但那样一来，检查所有借用就会变成一次
庞大的全程序分析，产生出令人匪夷所思的、毫无局部性可言的错误。Rust 的这套体系
意味着所有借用检查都可以在每个函数体内独立完成，你遇到的所有错误都应该相当
局部（否则就是你的类型签名写错了）。

可我们之前也在函数签名里写过引用啊，而且好好的！那是因为有些情形实在太常见了，
以至于 Rust 会自动替你挑好生命周期。这就是*生命周期省略*。

具体来说：

```rust ,ignore
// Only one reference in input, so the output must be derived from that input
fn foo(&A) -> &B; // sugar for:
fn foo<'a>(&'a A) -> &'a B;

// Many inputs, assume they're all independent
fn foo(&A, &B, &C); // sugar for:
fn foo<'a, 'b, 'c>(&'a A, &'b B, &'c C);

// Methods, assume all output lifetimes are derived from `self`
fn foo(&self, &B, &C) -> &D; // sugar for:
fn foo<'a, 'b, 'c>(&'a self, &'b B, &'c C) -> &'a D;
```

那么`fn foo<'a>(&'a A) -> &'a B`到底*意味着*什么？实际上，它的全部含义就是：
输入至少要和输出活得一样久。所以如果你把输出留在身边很长时间，
这就会扩大输入必须保持有效的区域。一旦你不再使用输出，
编译器就知道输入也可以随之失效了。

有了这套体系，Rust 就能保证不会有释放后使用，也不会在还有未了结的引用时
去修改东西。它要做的就是确保所有约束都能对上！

好了。那么。Iter。

我们回退到没有生命周期的状态：

```rust ,ignore
pub struct Iter<T> {
    next: Option<&Node<T>>,
}

impl<T> List<T> {
    pub fn iter(&self) -> Iter<T> {
        Iter { next: self.head.map(|node| &node) }
    }
}

impl<T> Iterator for Iter<T> {
    type Item = &T;
    fn next(&mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.next.map(|node| &node);
            &node.elem
        })
    }
}
```

我们只需要在函数和类型签名里加上生命周期：

```rust ,ignore
// Iter is generic over *some* lifetime, it doesn't care
pub struct Iter<'a, T> {
    next: Option<&'a Node<T>>,
}

// No lifetime here, List doesn't have any associated lifetimes
impl<T> List<T> {
    // We declare a fresh lifetime here for the *exact* borrow that
    // creates the iter. Now &self needs to be valid as long as the
    // Iter is around.
    pub fn iter<'a>(&'a self) -> Iter<'a, T> {
        Iter { next: self.head.map(|node| &node) }
    }
}

// We *do* have a lifetime here, because Iter has one that we need to define
impl<'a, T> Iterator for Iter<'a, T> {
    // Need it here too, this is a type declaration
    type Item = &'a T;

    // None of this needs to change, handled by the above.
    // Self continues to be incredibly hype and amazing
    fn next(&mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.next.map(|node| &node);
            &node.elem
        })
    }
}
```

好了，我觉得这回咱们成了。

```text
cargo build

error[E0308]: mismatched types
  --> src/second.rs:77:22
   |
77 |         Iter { next: self.head.map(|node| &node) }
   |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^ expected struct `second::Node`, found struct `std::boxed::Box`
   |
   = note: expected type `std::option::Option<&second::Node<T>>`
              found type `std::option::Option<&std::boxed::Box<second::Node<T>>>`

error[E0308]: mismatched types
  --> src/second.rs:85:25
   |
85 |             self.next = node.next.map(|node| &node);
   |                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^ expected struct `second::Node`, found struct `std::boxed::Box`
   |
   = note: expected type `std::option::Option<&'a second::Node<T>>`
              found type `std::option::Option<&std::boxed::Box<second::Node<T>>>`
```

(╯°□°)╯︵ ┻━┻

好。吧。我们修好了生命周期错误，但现在又冒出来一些新的类型错误。

我们想存的是`&Node`，但拿到的却是`&Box<Node>`。行吧，这够简单的，
我们只要在取引用之前先把 Box 解引用一下：

```rust ,ignore
impl<T> List<T> {
    pub fn iter<'a>(&'a self) -> Iter<'a, T> {
        Iter { next: self.head.map(|node| &*node) }
    }
}

impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;
    fn next(&mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.next.map(|node| &*node);
            &node.elem
        })
    }
}
```

```text
cargo build
   Compiling lists v0.1.0 (/Users/ADesires/dev/temp/lists)
error[E0515]: cannot return reference to local data `*node`
  --> src/second.rs:77:43
   |
77 |         Iter { next: self.head.map(|node| &*node) }
   |                                           ^^^^^^ returns a reference to data owned by the current function

error[E0507]: cannot move out of borrowed content
  --> src/second.rs:77:22
   |
77 |         Iter { next: self.head.map(|node| &*node) }
   |                      ^^^^^^^^^ cannot move out of borrowed content

error[E0515]: cannot return reference to local data `*node`
  --> src/second.rs:85:46
   |
85 |             self.next = node.next.map(|node| &*node);
   |                                              ^^^^^^ returns a reference to data owned by the current function

error[E0507]: cannot move out of borrowed content
  --> src/second.rs:85:25
   |
85 |             self.next = node.next.map(|node| &*node);
   |                         ^^^^^^^^^ cannot move out of borrowed content
```

(ﾉಥ益ಥ）ﾉ﻿ ┻━┻

我们忘了`as_ref`，于是就把 box 移动进了`map`，这意味着它会被丢弃，
也就意味着我们的引用会变成悬垂的：

```rust ,ignore
pub struct Iter<'a, T> {
    next: Option<&'a Node<T>>,
}

impl<T> List<T> {
    pub fn iter<'a>(&'a self) -> Iter<'a, T> {
        Iter { next: self.head.as_ref().map(|node| &*node) }
    }
}

impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;

    fn next(&mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.next.as_ref().map(|node| &*node);
            &node.elem
        })
    }
}
```

```text
cargo build
   Compiling lists v0.1.0 (/Users/ADesires/dev/temp/lists)
error[E0308]: mismatched types
  --> src/second.rs:77:22
   |
77 |         Iter { next: self.head.as_ref().map(|node| &*node) }
   |                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ expected struct `second::Node`, found struct `std::boxed::Box`
   |
   = note: expected type `std::option::Option<&second::Node<T>>`
              found type `std::option::Option<&std::boxed::Box<second::Node<T>>>`

error[E0308]: mismatched types
  --> src/second.rs:85:25
   |
85 |             self.next = node.next.as_ref().map(|node| &*node);
   |                         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ expected struct `second::Node`, found struct `std::boxed::Box`
   |
   = note: expected type `std::option::Option<&'a second::Node<T>>`
              found type `std::option::Option<&std::boxed::Box<second::Node<T>>>`

```

😭

`as_ref`又加了一层我们需要去掉的间接：


```rust ,ignore
pub struct Iter<'a, T> {
    next: Option<&'a Node<T>>,
}

impl<T> List<T> {
    pub fn iter<'a>(&'a self) -> Iter<'a, T> {
        Iter { next: self.head.as_deref() }
    }
}

impl<'a, T> Iterator for Iter<'a, T> {
    type Item = &'a T;

    fn next(&mut self) -> Option<Self::Item> {
        self.next.map(|node| {
            self.next = node.next.as_deref();
            &node.elem
        })
    }
}
```

```text
cargo build

```

🎉 🎉 🎉

as_deref 和 as_deref_mut 函数从 Rust 1.40 起就稳定了。在那之前你得写
`map(|node| &**node)`和`map(|node| &mut**node)`。你可能会想“哇那个`&**`
真是别扭得很”，你没想错，不过 Rust 就像好酒一样会随时间变得更好，
我们已经不需要那么写了。通常 Rust 非常擅长隐式地做这类转换，
靠的是一个叫做*解引用强制转换*的过程，基本上它能在你的代码里到处插入 \*，
好让类型检查通过。它之所以能这么干，是因为我们有借用检查器（borrow checker）来确保
永远不会把指针搞乱！

但在这个例子里，闭包再加上我们手里是`Option<&T>`而不是`&T`这一事实，
对它来说有点太复杂了，搞不定，所以我们得写明白一点来帮帮它。
好在按我的经验，这种情况相当少见。

纯粹为了完整起见，我们*可以*用*涡轮鱼*给它一个*不同的*提示：

```rust ,ignore
    self.next = node.next.as_ref().map::<&Node<T>, _>(|node| &node);
```

你看，map 是一个泛型函数：

```rust ,ignore
pub fn map<U, F>(self, f: F) -> Option<U>
```

涡轮鱼，也就是`::<>`，让我们能告诉编译器我们认为那些泛型参数的类型应该是什么。
在这里`::<&Node<T>, _>`说的是“它应该返回一个`&Node<T>`，
另外那个类型我不知道，也不关心”。

这反过来让编译器知道`&node`上应该施加解引用强制转换，
于是我们就不用手动去加那一堆 \* 了！

不过在这个例子里，我觉得这算不上什么改进，这不过是个拙劣的借口，
好让我炫一下解引用强制转换和偶尔有用的涡轮鱼罢了。😅

我们来写个测试，确认没把它写成空操作之类的：

```rust ,ignore
#[test]
fn iter() {
    let mut list = List::new();
    list.push(1); list.push(2); list.push(3);

    let mut iter = list.iter();
    assert_eq!(iter.next(), Some(&3));
    assert_eq!(iter.next(), Some(&2));
    assert_eq!(iter.next(), Some(&1));
}
```

```text
> cargo test

     Running target/debug/lists-5c71138492ad4b4a

running 5 tests
test first::test::basics ... ok
test second::test::basics ... ok
test second::test::into_iter ... ok
test second::test::iter ... ok
test second::test::peek ... ok

test result: ok. 4 passed; 0 failed; 0 ignored; 0 measured

```

爽。

最后需要指出的是，我们其实*可以*在这里应用生命周期省略：

```rust ,ignore
impl<T> List<T> {
    pub fn iter<'a>(&'a self) -> Iter<'a, T> {
        Iter { next: self.head.as_deref() }
    }
}
```

等价于：

```rust ,ignore
impl<T> List<T> {
    pub fn iter(&self) -> Iter<T> {
        Iter { next: self.head.as_deref() }
    }
}
```

耶，生命周期变少了！

或者，如果你不太喜欢把“结构体里含有生命周期”这件事“藏起来”，
可以使用 Rust 2018 的“显式省略生命周期”语法，也就是`'_`：

```rust ,ignore
impl<T> List<T> {
    pub fn iter(&self) -> Iter<'_, T> {
        Iter { next: self.head.as_deref() }
    }
}
```

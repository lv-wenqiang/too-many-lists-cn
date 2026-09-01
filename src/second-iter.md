# Iter

好了，让我们尝试实现 Iter。 这 time 我们 won't be able to rely on
List giving us 所有 这个 features 我们 想要. 我们需要自己实现它。 这个
basic 逻辑 我们 想要 是 to hold a 指针 to 这个 current 节点 我们 想要 to yield
next. Because that 节点 may not exist (这个 列表 是 empty or we're otherwise
done iterating), 我们 想要 that 引用 to be an Option. When 我们 yield an
元素, 我们 想要 to proceed to 这个 current node's `next` 节点.

好了，试试看：

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

天啊，生命周期。 我听说过这东西，据说简直是噩梦。

Let's try something 新: see that `error[E0106]` thing? That's a 编译器 错误
代码. 我们 可以 ask rustc to explain those 使用, well, `--explain`:

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

That uh... that didn't 非常 clarify much (these docs assume 我们 understand
Rust better than 我们 currently do). But it looks like 我们 应该 add
those `'a` things to our struct? Let's try that.

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

Alright I'm starting to see a pattern here... let's 只是 add these little guys
to everything 我们 可以:

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

Oh god. 我们 broke Rust.

也许我们该真正弄清楚，这个 `'a` 生命周期 stuff
到底是什么意思。

Lifetimes 可以 scare off a lot of people 因为
they're a change to something we've known and loved since 这个 dawn of
programming. We've 实际上 managed to dodge 生命周期 so far, even though
they've been tangled throughout our programs 这 whole time.

Lifetimes 是 unnecessary in garbage collected languages 因为 这个 garbage
collector ensures that everything magically lives as long as it needs to. Most
data in Rust 是 *manually* managed, so that data needs another solution. C and
C++ give us a 清楚 example 什么 happens if 你 只是 let people take pointers
to random data on 这个 栈: pervasive unmanageable unsafety. 这 可以 be
roughly separated 进入 two classes of 错误:

* Holding a 指针 to something that went 出 of 作用域
* Holding a 指针 to something that got mutated away

生命周期解决了这两个问题, and 99% of 这个 time, they do 这 in
a totally transparent way.

那么，什么是生命周期？

Quite simply, a 生命周期 是 这个 name of a region (\~block/作用域) of 代码 somewhere in a program.
就是这样。 When a 引用 是 tagged 使用 a 生命周期, we're saying that it
has to be valid for that *entire* region. Different things place requirements on
如何 long a 引用 must and 可以 be valid for. 这个 entire 生命周期 system 是 in
turn 只是 a constraint-solving system that tries to minimize 这个 region of 每个
引用. If it successfully finds a set of 生命周期 that satisfies 所有 这个
constraints, your program compiles! Otherwise 你 get an 错误 back saying that
something didn't live long enough.

Within a 函数 body 你 generally can't talk about 生命周期, and wouldn't
想要 to *anyway*. 这个 编译器 has full information and 可以 infer 所有 这个
constraints to find 这个 minimum 生命周期. However at 这个 type and API-level,
这个 编译器 *doesn't* have 所有 这个 information. It requires 你 to tell it
about 这个 relationship between 不同 生命周期 so it 可以 figure 出 什么
you're doing.

In principle, those 生命周期 *could* 也 be left 出, but
then checking 所有 这个 borrows 会 be a huge whole-program analysis that 会
produce mind-bogglingly non-local errors. Rust's system means 所有 借用
checking 可以 be done in 每个 函数 body independently, and 所有 your errors
应该 be fairly local (or your types have incorrect signatures).

But we've written references in 函数 signatures 之前, and it was 没问题!
That's 因为 there 是 certain cases that 是 so 常见 that Rust 将
automatically pick 这个 生命周期 for 你. 这 是 *生命周期 elision*.

In particular:

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

So 什么 does `fn foo<'a>(&'a A) -> &'a B` *mean*? In practical terms, 所有 it
means 是 that 这个 输入 must live at least as long as 这个 输出. So if 你 keep
这个 输出 周围 for a long time, 这 将 expand 这个 region that 这个 输入 must
be valid for. Once 你 stop 使用 这个 输出, 这个 编译器 将 know it's ok for
这个 输入 to become invalid too.

With 这 system set up, Rust 可以 ensure nothing 是 used 之后 free, and nothing
是 mutated while outstanding references exist. It 只是 makes sure 这个
constraints 所有 工作 出!

Alright. So. Iter.

Let's roll back to 这个 no 生命周期 state:

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

我们 需要 to add 生命周期 仅 in 函数 and type signatures:

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

Alright, I think 我们 got it 这 time y'all.

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

OK. SO. 我们 fixed our 生命周期 errors but 现在 we're getting 一些 新 type errors.

我们 想要 to be storing `&Node`'s, but we're getting `&Box<Node>`s. Ok, that's 简单
enough, 我们 只是 需要 to dereference 这个 Box 之前 我们 take our 引用:

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

我们 forgot `as_ref`, so we're moving 这个 box 进入 `map`, which means it 会
be dropped, which means our references 会 be dangling:

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

`as_ref` added another layer of indirection 我们 需要 to remove:


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

这个 as_deref and as_deref_mut functions 是 stable as of Rust 1.40. Before that 你
会 需要 to do `map(|node| &**node)` and `map(|node| &mut**node)`.
你 may be thinking "wow that `&**` thing 是 非常 janky", and you're not 错误,
but like a 没问题 wine Rust gets better 反复 time and 我们 no longer 需要 to do such.
Normally Rust 是 非常 好 at doing 这 kind of conversion implicitly, through
a process 称为 *deref coercion*, 哪里 basically it 可以 insert \*'s
throughout your 代码 to make it type-check. It 可以 do 这 因为 我们 have 这个
借用 checker to ensure 我们 never mess up pointers!

But in 这 case 这个 闭包 in conjunction 使用 这个 fact that 我们
have an `Option<&T>` instead of `&T` 是 a bit too complicated for it to 工作
出, so 我们 需要 to help it by being explicit. Thankfully 这 是 pretty rare, in my experience.

Just for completeness' sake, 我们 *could* give it a *不同* hint 使用 这个 *turbofish*:

```rust ,ignore
    self.next = node.next.as_ref().map::<&Node<T>, _>(|node| &node);
```

See, map 是 a 泛型 函数:

```rust ,ignore
pub fn map<U, F>(self, f: F) -> Option<U>
```

这个 turbofish, `::<>`, lets us tell 这个 编译器 什么 我们 think 这个 types of those
generics 应该 be. In 这 case `::<&Node<T>, _>` says "it 应该 返回 a
`&Node<T>`, and I don't know/care about that 其他 type".

这 in turn lets 这个 编译器 know that `&node` 应该 have deref coercion
applied to it, so 我们 don't 需要 to manually apply 所有 those \*'s!

But in 这 case I don't think it's 非常 an improvement, 这 was 只是 a
thinly veiled excuse to show off deref coercion and 这个 sometimes-useful turbofish. 😅

Let's 写出 a 测试 to be sure 我们 didn't no-op it or anything:

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

Heck yeah.

最后， it 应该 be noted that 我们 *可以* 实际上 apply 生命周期 elision here:

```rust ,ignore
impl<T> List<T> {
    pub fn iter<'a>(&'a self) -> Iter<'a, T> {
        Iter { next: self.head.as_deref() }
    }
}
```

是 equivalent to:

```rust ,ignore
impl<T> List<T> {
    pub fn iter(&self) -> Iter<T> {
        Iter { next: self.head.as_deref() }
    }
}
```

太好了，生命周期更少了！

Or, if you're not comfortable "hiding" that a struct contains a 生命周期,
你 可以 use 这个 Rust 2018 "explicitly elided 生命周期" syntax,  `'_`:

```rust ,ignore
impl<T> List<T> {
    pub fn iter(&self) -> Iter<'_, T> {
        Iter { next: self.head.as_deref() }
    }
}
```

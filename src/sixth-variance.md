# 型变与 PhantomData

现在把这件事往后拖、以后再修会很烦人，所以我们现在就把硬核布局的事情办了。

制作不安全 Rust 集合有五位可怕的天启骑士：

1. [型变](https://doc.rust-lang.org/nightly/nomicon/subtyping.html)
2. [Drop 检查](https://doc.rust-lang.org/nightly/nomicon/dropck.html)
3. [NonNull 优化](https://doc.rust-lang.org/nightly/std/ptr/struct.NonNull.html)
4. [isize::MAX 分配规则](https://doc.rust-lang.org/nightly/nomicon/vec/vec-alloc.html)
5. [零大小类型](https://doc.rust-lang.org/nightly/nomicon/vec/vec-zsts.html)

谢天谢地，后两位不会给我们添麻烦。

第三位我们*可以*把它变成自己的麻烦，但那样得不偿失——如果你都已经选择用 LinkedList 了，那你在内存效率这场仗上早就投降一百次了。

第二位曾经是我坚称非常重要、而且 std 还要拿它折腾一番的东西；不过默认行为是安全的，能拿它折腾的手段都是不稳定的，而且你得*非常非常努力*才会注意到默认行为的局限，所以，别操心了。

这就只剩下型变了。老实说，这个你大概也可以往后拖，但作为一个搞集合的人我还是有我的骄傲，所以我们要把型变这件事办了。

那么，惊喜：Rust 是有子类型关系的。具体来说，`&'big T`是`&'small T`的一个*子类型*。为什么？因为如果某段代码需要一个在程序某个特定区域内存活的引用，那么给它一个存活得*更久*的引用通常是完全没问题的。直觉上这就是对的，不是吗？

这为什么重要？想象一段接受两个同类型值的代码：

```rust ,ignore
fn take_two<T>(_val1: T, _val2: T) { }
```

这段代码无聊透顶，所以我们应该指望它在 T=&u32 时也能正常工作，对吧？

```rust
fn two_refs<'big: 'small, 'small>(
    big: &'big u32, 
    small: &'small u32,
) {
    take_two(big, small);
}

fn take_two<T>(_val1: T, _val2: T) { }
```

没错，编译得好好的！

现在我们来找点乐子，把它包进，哦，我想想，`std::cell::Cell`里：

```rust ,compilefail
use std::cell::Cell;

fn two_refs<'big: 'small, 'small>(
    // NOTE: these two lines changed
    big: Cell<&'big u32>, 
    small: Cell<&'small u32>,
) {
    take_two(big, small);
}

fn take_two<T>(_val1: T, _val2: T) { }
```

```text
error[E0623]: lifetime mismatch
 --> src/main.rs:7:19
  |
4 |     big: Cell<&'big u32>, 
  |               ---------
5 |     small: Cell<&'small u32>,
  |                 ----------- these two types are declared with different lifetimes...
6 | ) {
7 |     take_two(big, small);
  |                   ^^^^^ ...but data from `small` flows into `big` here
```

啊？？？我们又没动生命周期，编译器现在生什么气啊！？

好吧，生命周期的“子类型”那套东西一定是相当简单的，所以你一旦把引用包进任何东西里它就崩了，你看，用 Vec 也一样会挂：

```rust
fn two_refs<'big: 'small, 'small>(
    big: Vec<&'big u32>, 
    small: Vec<&'small u32>,
) {
    take_two(big, small);
}

fn take_two<T>(_val1: T, _val2: T) { }
```

```text
    Finished dev [unoptimized + debuginfo] target(s) in 1.07s
     Running `target/debug/playground`
```

看吧，它也编译不——等等什么？？？Vec 是有魔法的吗？？？？？？

嗯，是的。但也不是。魔法一直都在我们体内，而那个魔法就是 ✨*型变*✨。

如果你想看所有血淋淋的细节，去读[死灵书中关于子类型关系的一章](https://doc.rust-lang.org/nightly/nomicon/subtyping.html)；不过基本上，子类型关系*并不*总是安全的。特别是当涉及可变引用时它就不安全了，因为你可以用`mem::swap`之类的东西，然后哎呀，悬垂指针！

那些“像可变引用一样”的东西是*不变*的，也就是说它们会阻止子类型关系在其泛型参数上发生。所以为了安全，`&mut T`对 T 是不变的，而`Cell<T>`对 T 也是不变的，因为`&Cell<T>`基本上就是`&mut T`（因为内部可变性）。

几乎所有不是不变的东西都是*协变*的，这就是说子类型关系会“穿过”它并继续正常工作（另外还有*逆变*类型，它们让子类型关系反过来，但这类东西非常罕见，而且没人喜欢它们，所以我不会再提了）。

集合通常包含一个指向其数据的可变指针，所以你可能会以为它们也是不变的；可事实上，它们不需要如此！由于 Rust 的所有权系统，`Vec<T>`在语义上等价于`T`，这就意味着让它协变是安全的！

不幸的是，下面这个定义是不变的：

```rust
pub struct LinkedList<T> {
    front: Link<T>,
    back: Link<T>,
    len: usize,
}

type Link<T> = *mut Node<T>;

struct Node<T> {
    front: Link<T>,
    back: Link<T>,
    elem: T, 
}
```

那 Rust 究竟是怎么判定这些东西的型变的呢？嗯，在 1.0 之前那些美好的旧时光里，我们曾折腾过让人们直接指定自己想要的型变，然后……那是一场彻头彻尾的车祸现场！子类型关系和型变实在太难绕明白了，连核心开发者们在基本术语上都真心谈不拢！所以我们转向了“按实例推导型变”的做法：编译器直接看你的字段，把它们的型变照抄过来。只要出现任何分歧，永远是不变性获胜，因为那样才安全。

那我们的类型定义里有什么让 Rust 生气的东西呢？`*mut`！

Rust 里的原始指针基本上就是尽量让你想干嘛干嘛，但它们恰好有一项安全特性：因为大多数人压根不知道 Rust 里还有型变和子类型关系这回事，而*错误地*协变又会极其危险，所以`*mut T`是不变的——毕竟它很有可能正被“当作”`&mut T`使用。

对我这样一个花了大量时间在 Rust 里写集合的人来说，这实在烦人透顶。所以当我做 [std::ptr::NonNull](https://doc.rust-lang.org/std/ptr/struct.NonNull.html) 的时候，我加了这么一小段魔法：

> 与`*mut T`不同，`NonNull<T>`被设计成对`T`协变。这使得在构建协变类型时可以使用`NonNull<T>`，但如果把它用在本不该协变的类型里，就会带来不可靠的风险。

可是等等，它的接口是围绕`*mut T`建起来的，这是怎么回事！难道真是魔法？！我们来看看：

```rust
pub struct NonNull<T> {
    pointer: *const T,
}


impl<T> NonNull<T> {
    pub unsafe fn new_unchecked(ptr: *mut T) -> Self {
        // SAFETY: the caller must guarantee that `ptr` is non-null.
        unsafe { NonNull { pointer: ptr as *const T } }
    }
}
```

并没有。这儿没有魔法！NonNull 不过是钻了`*const T`是协变的这个空子，把它存起来，然后在 API 边界上来回转换成`*mut T`，好让它“看起来像”存的是`*mut T`。整个把戏就这么回事！Rust 里的集合就是这样做到协变的！这也太惨了！所以我做了“好指针类型”替你完成这件事！不用谢！好好享受你的子类型关系走火枪吧！

解决你一切问题的办法就是使用 NonNull，然后如果你想要重新拥有可空指针，就用`Option<NonNull<T>>`。我们真要费这个劲吗……？

要！这很糟，但我们做的是*生产级链表*，所以我们要把蔬菜全吃光，用最难的方式做事（我们本可以直接用裸`*const T`然后到处转换，可我是真心想看看这有多痛苦……为了人体工程学科学）。


于是这就是我们最终的类型定义：

```rust
use std::ptr::NonNull;

// !!!This changed!!!
pub struct LinkedList<T> {
    front: Link<T>,
    back: Link<T>,
    len: usize,
}

type Link<T> = Option<NonNull<Node<T>>>;

struct Node<T> {
    front: Link<T>,
    back: Link<T>,
    elem: T, 
}
```

……等等不对，还有最后一件事。任何时候你摆弄原始指针，都该加一个幽灵来守护你的指针：

```rust ,ignore
use std::marker::PhantomData;

pub struct LinkedList<T> {
    front: Link<T>,
    back: Link<T>,
    len: usize,
    /// We semantically store values of T by-value.
    _boo: PhantomData<T>,
}
```

在这个例子里我不认为我们*真的*需要 [PhantomData](https://doc.rust-lang.org/std/marker/struct.PhantomData.html)，但任何时候你*确实*用了 NonNull（或者一般意义上的原始指针），都应该加上它以求稳妥，并且把你*自认为*在做的事情清楚地告诉编译器和其他人。

PhantomData 是一种办法，让我们能给编译器一个额外的“示例”字段——这个字段在概念上存在于你的类型中，却因为各种原因（间接、类型擦除，等等）实际上并不存在。在这个例子里，我们用了 NonNull，因为我们主张自己的类型表现得“仿佛”它存储了一个 T 值，所以我们加上一个 PhantomData 把这一点挑明。

标准库其实还有别的理由这么做，因为它能用上那个该死的 [Drop 检查覆盖](https://doc.rust-lang.org/nightly/nomicon/dropck.html)；不过那个特性被翻来覆去改了太多次，我其实已经不知道 PhantomData 这一招对它来说*是否*还成立了。我还是会把它当邪教教条一样奉行到永远，因为 Drop 检查的魔法已经烙进我脑子里了！

（Node 是字面意义上存着一个 T 的，所以它不必这么干，好耶！）

……好了，这回布局是真的搞完了！接下来是真正的基础功能！
